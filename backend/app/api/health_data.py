from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from datetime import datetime, timezone, timedelta
from typing import List, Optional
from statistics import mean

from app.database import get_db
from app.api.auth import get_current_user
from app.models.user import User
from app.models.health_data import SleepRecord, ActivityRecord, NutritionRecord, BodyMetric, HydrationRecord
from app.models.integration import Integration
from app.schemas.health_data import (
    SleepRecordResponse, ActivityRecordResponse, NutritionRecordResponse,
    BodyMetricResponse, HydrationRecordResponse, DashboardSummary
)

router = APIRouter(prefix="/health", tags=["Health Data"])


@router.get("/dashboard", response_model=DashboardSummary)
def get_dashboard(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    cutoff_7d = datetime.now(timezone.utc) - timedelta(days=7)
    cutoff_30d = datetime.now(timezone.utc) - timedelta(days=30)

    latest_sleep = (
        db.query(SleepRecord)
        .filter_by(user_id=current_user.id)
        .order_by(SleepRecord.start_time.desc())
        .first()
    )
    latest_body = (
        db.query(BodyMetric)
        .filter_by(user_id=current_user.id)
        .order_by(BodyMetric.measured_at.desc())
        .first()
    )
    latest_activity = (
        db.query(ActivityRecord)
        .filter_by(user_id=current_user.id)
        .order_by(ActivityRecord.start_time.desc())
        .first()
    )

    # 7-day sleep averages
    sleep_7d = (
        db.query(SleepRecord)
        .filter(SleepRecord.user_id == current_user.id, SleepRecord.start_time >= cutoff_7d)
        .all()
    )
    sleep_durations = [r.total_duration_minutes for r in sleep_7d if r.total_duration_minutes]
    sleep_scores = [r.sleep_score for r in sleep_7d if r.sleep_score]
    hrv_values = [r.hrv for r in sleep_7d if r.hrv]
    recovery_scores = [r.recovery_score for r in sleep_7d if r.recovery_score]

    # 7-day nutrition
    nutrition_7d = (
        db.query(NutritionRecord)
        .filter(NutritionRecord.user_id == current_user.id, NutritionRecord.recorded_date >= cutoff_7d)
        .all()
    )
    total_calories = sum(r.calories or 0 for r in nutrition_7d)

    # 7-day steps
    activity_7d = (
        db.query(ActivityRecord)
        .filter(ActivityRecord.user_id == current_user.id, ActivityRecord.start_time >= cutoff_7d)
        .all()
    )
    total_steps = sum(r.steps or 0 for r in activity_7d)

    # Hydration
    hydration_7d = (
        db.query(HydrationRecord)
        .filter(HydrationRecord.user_id == current_user.id, HydrationRecord.recorded_at >= cutoff_7d)
        .all()
    )
    hydration_by_day: dict = {}
    for h in hydration_7d:
        day = h.recorded_at.strftime("%Y-%m-%d")
        hydration_by_day[day] = hydration_by_day.get(day, 0) + (h.amount_ml or h.daily_total_ml or 0)
    avg_hydration = mean(hydration_by_day.values()) if hydration_by_day else None

    # Trends (30 days)
    body_30d = (
        db.query(BodyMetric)
        .filter(BodyMetric.user_id == current_user.id, BodyMetric.measured_at >= cutoff_30d)
        .order_by(BodyMetric.measured_at.asc())
        .all()
    )
    sleep_30d = (
        db.query(SleepRecord)
        .filter(SleepRecord.user_id == current_user.id, SleepRecord.start_time >= cutoff_30d)
        .order_by(SleepRecord.start_time.asc())
        .all()
    )
    activity_30d = (
        db.query(ActivityRecord)
        .filter(ActivityRecord.user_id == current_user.id, ActivityRecord.start_time >= cutoff_30d)
        .order_by(ActivityRecord.start_time.asc())
        .all()
    )

    connected = db.query(Integration).filter_by(user_id=current_user.id, is_connected=True).count()

    return DashboardSummary(
        latest_sleep=SleepRecordResponse.model_validate(latest_sleep) if latest_sleep else None,
        latest_body_metric=BodyMetricResponse.model_validate(latest_body) if latest_body else None,
        latest_activity=ActivityRecordResponse.model_validate(latest_activity) if latest_activity else None,
        avg_sleep_duration_7d=mean(sleep_durations) if sleep_durations else None,
        avg_sleep_score_7d=mean(sleep_scores) if sleep_scores else None,
        avg_hrv_7d=mean(hrv_values) if hrv_values else None,
        avg_recovery_score_7d=mean(recovery_scores) if recovery_scores else None,
        total_calories_7d=total_calories or None,
        avg_daily_calories_7d=total_calories / 7 if total_calories else None,
        total_steps_7d=total_steps or None,
        avg_hydration_7d=avg_hydration,
        weight_trend=[
            {"date": r.measured_at.strftime("%Y-%m-%d"), "value": r.weight_kg}
            for r in body_30d if r.weight_kg
        ],
        sleep_trend=[
            {"date": r.start_time.strftime("%Y-%m-%d"), "duration": r.total_duration_minutes,
             "score": r.sleep_score, "hrv": r.hrv, "recovery": r.recovery_score}
            for r in sleep_30d
        ],
        activity_trend=[
            {"date": r.start_time.strftime("%Y-%m-%d"), "calories": r.calories_burned,
             "strain": r.strain_score, "type": r.activity_type}
            for r in activity_30d
        ],
        hrv_trend=[
            {"date": r.start_time.strftime("%Y-%m-%d"), "hrv": r.hrv}
            for r in sleep_30d if r.hrv
        ],
        connected_integrations=connected,
    )


@router.get("/sleep", response_model=List[SleepRecordResponse])
def get_sleep(
    days: int = Query(default=30, le=365),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    return (
        db.query(SleepRecord)
        .filter(SleepRecord.user_id == current_user.id, SleepRecord.start_time >= cutoff)
        .order_by(SleepRecord.start_time.desc())
        .all()
    )


@router.get("/activity", response_model=List[ActivityRecordResponse])
def get_activity(
    days: int = Query(default=30, le=365),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    return (
        db.query(ActivityRecord)
        .filter(ActivityRecord.user_id == current_user.id, ActivityRecord.start_time >= cutoff)
        .order_by(ActivityRecord.start_time.desc())
        .all()
    )


@router.get("/nutrition", response_model=List[NutritionRecordResponse])
def get_nutrition(
    days: int = Query(default=30, le=365),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    return (
        db.query(NutritionRecord)
        .filter(NutritionRecord.user_id == current_user.id, NutritionRecord.recorded_date >= cutoff)
        .order_by(NutritionRecord.recorded_date.desc())
        .all()
    )


@router.get("/body", response_model=List[BodyMetricResponse])
def get_body_metrics(
    days: int = Query(default=90, le=365),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    return (
        db.query(BodyMetric)
        .filter(BodyMetric.user_id == current_user.id, BodyMetric.measured_at >= cutoff)
        .order_by(BodyMetric.measured_at.desc())
        .all()
    )


@router.get("/hydration", response_model=List[HydrationRecordResponse])
def get_hydration(
    days: int = Query(default=30, le=365),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    return (
        db.query(HydrationRecord)
        .filter(HydrationRecord.user_id == current_user.id, HydrationRecord.recorded_at >= cutoff)
        .order_by(HydrationRecord.recorded_at.desc())
        .all()
    )
