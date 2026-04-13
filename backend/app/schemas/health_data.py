from pydantic import BaseModel
from typing import Optional, List, Any, Dict
from datetime import datetime


class SleepRecordResponse(BaseModel):
    id: int
    source: str
    start_time: datetime
    end_time: datetime
    total_duration_minutes: Optional[int]
    sleep_efficiency: Optional[float]
    deep_sleep_minutes: Optional[int]
    light_sleep_minutes: Optional[int]
    rem_sleep_minutes: Optional[int]
    awake_minutes: Optional[int]
    sleep_score: Optional[float]
    recovery_score: Optional[float]
    avg_heart_rate: Optional[float]
    hrv: Optional[float]
    avg_spo2: Optional[float]
    respiratory_rate: Optional[float]
    created_at: datetime

    model_config = {"from_attributes": True}


class ActivityRecordResponse(BaseModel):
    id: int
    source: str
    activity_type: Optional[str]
    start_time: datetime
    end_time: Optional[datetime]
    duration_minutes: Optional[int]
    calories_burned: Optional[float]
    avg_heart_rate: Optional[float]
    max_heart_rate: Optional[float]
    strain_score: Optional[float]
    steps: Optional[int]
    distance_km: Optional[float]
    workout_name: Optional[str]
    total_volume_kg: Optional[float]
    created_at: datetime

    model_config = {"from_attributes": True}


class NutritionRecordResponse(BaseModel):
    id: int
    source: str
    recorded_date: datetime
    meal_type: Optional[str]
    calories: Optional[float]
    protein_g: Optional[float]
    carbs_g: Optional[float]
    fat_g: Optional[float]
    fiber_g: Optional[float]
    sugar_g: Optional[float]
    sodium_mg: Optional[float]
    food_items: Optional[List[Any]]
    created_at: datetime

    model_config = {"from_attributes": True}


class BodyMetricResponse(BaseModel):
    id: int
    source: str
    measured_at: datetime
    weight_kg: Optional[float]
    bmi: Optional[float]
    body_fat_percent: Optional[float]
    muscle_mass_kg: Optional[float]
    bone_mass_kg: Optional[float]
    water_percent: Optional[float]
    visceral_fat: Optional[float]
    metabolic_age: Optional[int]
    systolic_bp: Optional[int]
    diastolic_bp: Optional[int]
    pulse: Optional[int]
    created_at: datetime

    model_config = {"from_attributes": True}


class HydrationRecordResponse(BaseModel):
    id: int
    source: str
    recorded_at: datetime
    amount_ml: Optional[float]
    daily_total_ml: Optional[float]
    daily_goal_ml: Optional[float]
    created_at: datetime

    model_config = {"from_attributes": True}


class HealthMetricResponse(BaseModel):
    id: int
    source: str
    metric_type: str
    value: Optional[float]
    unit: Optional[str]
    recorded_at: datetime

    model_config = {"from_attributes": True}


class DashboardSummary(BaseModel):
    # Latest values
    latest_sleep: Optional[SleepRecordResponse]
    latest_body_metric: Optional[BodyMetricResponse]
    latest_activity: Optional[ActivityRecordResponse]

    # 7-day averages
    avg_sleep_duration_7d: Optional[float]
    avg_sleep_score_7d: Optional[float]
    avg_hrv_7d: Optional[float]
    avg_recovery_score_7d: Optional[float]
    total_calories_7d: Optional[float]
    avg_daily_calories_7d: Optional[float]
    total_steps_7d: Optional[int]
    avg_hydration_7d: Optional[float]

    # Trends
    weight_trend: Optional[List[Dict]]
    sleep_trend: Optional[List[Dict]]
    activity_trend: Optional[List[Dict]]
    hrv_trend: Optional[List[Dict]]

    # Connected integrations count
    connected_integrations: int
