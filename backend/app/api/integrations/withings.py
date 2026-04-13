"""
Withings Health API Integration
Docs: https://developer.withings.com/api-reference
OAuth2 flow.
Provides: weight, body composition, blood pressure, sleep, activity
"""
from datetime import datetime, timezone, timedelta
from typing import Optional
import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
import time

from app.database import get_db
from app.models.integration import Integration, SyncLog
from app.models.health_data import BodyMetric, SleepRecord, ActivityRecord
from app.api.auth import get_current_user
from app.models.user import User
from app.config import get_settings

router = APIRouter(prefix="/withings")
settings = get_settings()
PLATFORM = "withings"


def _get_integration(user: User, db: Session) -> Optional[Integration]:
    return db.query(Integration).filter_by(user_id=user.id, platform=PLATFORM).first()


async def _refresh_token_if_needed(integration: Integration, db: Session):
    if not integration.token_expires_at:
        return
    if datetime.now(timezone.utc) < integration.token_expires_at - timedelta(minutes=5):
        return
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            settings.withings_token_url,
            data={
                "action": "requesttoken",
                "grant_type": "refresh_token",
                "client_id": settings.withings_client_id,
                "client_secret": settings.withings_client_secret,
                "refresh_token": integration.refresh_token,
            },
        )
        if resp.status_code == 200:
            body = resp.json().get("body", {})
            integration.access_token = body.get("access_token")
            integration.refresh_token = body.get("refresh_token")
            if body.get("expires_in"):
                integration.token_expires_at = datetime.now(timezone.utc) + timedelta(
                    seconds=body["expires_in"]
                )
            db.commit()


@router.get("/connect")
async def connect_withings(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    integration = _get_integration(current_user, db)
    if not integration:
        integration = Integration(user_id=current_user.id, platform=PLATFORM)
        db.add(integration)
        db.commit()

    params = {
        "response_type": "code",
        "client_id": settings.withings_client_id,
        "redirect_uri": settings.withings_redirect_uri,
        "scope": "user.info,user.metrics,user.activity,user.sleepevents",
        "state": str(current_user.id),
    }
    query = "&".join(f"{k}={v}" for k, v in params.items())
    return {"auth_url": f"{settings.withings_auth_url}?{query}"}


@router.get("/callback")
async def withings_callback(
    code: str = Query(...),
    state: str = Query(...),
    db: Session = Depends(get_db)
):
    user_id = int(state)
    integration = db.query(Integration).filter_by(user_id=user_id, platform=PLATFORM).first()
    if not integration:
        raise HTTPException(status_code=400, detail="Integration not found")

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            settings.withings_token_url,
            data={
                "action": "requesttoken",
                "grant_type": "authorization_code",
                "client_id": settings.withings_client_id,
                "client_secret": settings.withings_client_secret,
                "code": code,
                "redirect_uri": settings.withings_redirect_uri,
            },
        )
    if resp.status_code != 200:
        raise HTTPException(status_code=400, detail=f"Token exchange failed: {resp.text}")

    body = resp.json().get("body", {})
    integration.access_token = body.get("access_token")
    integration.refresh_token = body.get("refresh_token")
    integration.token_scope = body.get("scope")
    if body.get("expires_in"):
        integration.token_expires_at = datetime.now(timezone.utc) + timedelta(
            seconds=body["expires_in"]
        )
    integration.platform_user_id = str(body.get("userid", ""))
    integration.is_connected = True
    db.commit()

    return RedirectResponse(f"{settings.frontend_url}/integrations?connected=withings")


@router.post("/disconnect")
async def disconnect_withings(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    integration = _get_integration(current_user, db)
    if integration:
        integration.is_connected = False
        integration.access_token = None
        integration.refresh_token = None
        db.commit()
    return {"status": "disconnected"}


# Withings measure types
BODY_MEASURE_TYPES = {
    1: ("weight_kg", 1),         # Weight in grams -> kg
    6: ("body_fat_percent", 1),  # Fat ratio in %
    8: ("fat_free_mass_kg", 1),  # Fat Free Mass in grams -> kg
    11: ("pulse", 1),            # Heart Pulse (bpm)
    9: ("diastolic_bp", 1),      # Diastolic Blood Pressure mmHg
    10: ("systolic_bp", 1),      # Systolic Blood Pressure mmHg
    76: ("muscle_mass_kg", 1),   # Muscle mass grams -> kg
    77: ("bone_mass_kg", 1),     # Bone mass grams -> kg
    88: ("bmi", 1),              # BMI
    170: ("visceral_fat", 1),    # Visceral fat
    174: ("metabolic_age", 1),   # Metabolic age
    226: ("water_percent", 1),   # Hydration %
}


@router.post("/sync")
async def sync_withings(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    days: int = Query(default=30, le=365)
):
    integration = _get_integration(current_user, db)
    if not integration or not integration.is_connected:
        raise HTTPException(status_code=400, detail="Withings not connected")

    await _refresh_token_if_needed(integration, db)

    log = SyncLog(integration_id=integration.id)
    db.add(log)
    db.commit()

    synced = 0
    headers = {"Authorization": f"Bearer {integration.access_token}"}
    start_ts = int((datetime.now(timezone.utc) - timedelta(days=days)).timestamp())

    async with httpx.AsyncClient(timeout=30) as client:
        # Body measurements
        resp = await client.post(
            f"{settings.withings_api_base}/measure",
            headers=headers,
            data={"action": "getmeas", "meastype": "1,6,8,9,10,11,76,77,88", "startdate": start_ts},
        )
        if resp.status_code == 200:
            data = resp.json().get("body", {})
            for grp in data.get("measuregrps", []):
                measured_at = datetime.fromtimestamp(grp["date"], tz=timezone.utc)
                metric_values = {}
                for m in grp.get("measures", []):
                    if m["type"] in BODY_MEASURE_TYPES:
                        field, _ = BODY_MEASURE_TYPES[m["type"]]
                        value = m["value"] * (10 ** m["unit"])
                        metric_values[field] = value

                if metric_values:
                    body = BodyMetric(
                        user_id=current_user.id,
                        source=PLATFORM,
                        measured_at=measured_at,
                        raw_data=grp,
                        **metric_values
                    )
                    db.add(body)
                    synced += 1

        # Sleep data
        resp = await client.post(
            f"{settings.withings_api_base}/v2/sleep",
            headers=headers,
            data={"action": "getsummary", "startdateymd": (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")},
        )
        if resp.status_code == 200:
            for record in resp.json().get("body", {}).get("series", []):
                data = record.get("data", {})
                sleep = SleepRecord(
                    user_id=current_user.id,
                    source=PLATFORM,
                    external_id=str(record.get("id", "")),
                    start_time=datetime.fromtimestamp(record["startdate"], tz=timezone.utc),
                    end_time=datetime.fromtimestamp(record["enddate"], tz=timezone.utc),
                    deep_sleep_minutes=int(data.get("deepsleepduration", 0) / 60),
                    light_sleep_minutes=int(data.get("lightsleepduration", 0) / 60),
                    rem_sleep_minutes=int(data.get("remsleepduration", 0) / 60),
                    awake_minutes=int(data.get("wakeupduration", 0) / 60),
                    avg_heart_rate=data.get("hr_average"),
                    avg_spo2=data.get("sleep_score"),
                    hrv=data.get("rmssd"),
                    respiratory_rate=data.get("breathing_disturbances_intensity"),
                    raw_data=record,
                )
                db.add(sleep)
                synced += 1

    integration.last_synced_at = datetime.now(timezone.utc)
    log.status = "success"
    log.records_synced = synced
    log.completed_at = datetime.now(timezone.utc)
    db.commit()

    return {"status": "success", "records_synced": synced}
