"""
Renpho Smart Scale Integration
Renpho does not have an official public API. Data sync is achieved through:
1. Renpho's internal API (email/password auth - reverse-engineered, may break)
2. CSV export import from the Renpho app (Settings > Export Data)
3. Google Fit / Apple Health bridge (if user syncs Renpho to those)
"""
from datetime import datetime, timezone, timedelta
from typing import Optional
import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from sqlalchemy.orm import Session
import csv, io

from app.database import get_db
from app.models.integration import Integration, SyncLog
from app.models.health_data import BodyMetric
from app.api.auth import get_current_user
from app.models.user import User
from app.config import get_settings

router = APIRouter(prefix="/renpho")
settings = get_settings()
PLATFORM = "renpho"

# Renpho internal API endpoints (unofficial)
RENPHO_AUTH_URL = "https://renphohealth.com/api/reach/user/login"
RENPHO_MEASURE_URL = "https://renphohealth.com/api/reach/measurements/list.json"


def _get_integration(user: User, db: Session) -> Optional[Integration]:
    return db.query(Integration).filter_by(user_id=user.id, platform=PLATFORM).first()


@router.post("/connect")
async def connect_renpho(
    email: str,
    password: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Authenticate with Renpho using email/password.
    Note: Renpho does not have a public OAuth API. This uses their internal API.
    """
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            RENPHO_AUTH_URL,
            json={"email": email, "password": password, "terminal_user_session_key": ""},
            headers={"Content-Type": "application/json"},
        )

    if resp.status_code != 200:
        raise HTTPException(status_code=401, detail="Renpho authentication failed")

    data = resp.json()
    session_key = data.get("terminal_user_session_key") or data.get("session_key")
    if not session_key:
        raise HTTPException(status_code=401, detail="No session key received from Renpho")

    integration = _get_integration(current_user, db)
    if not integration:
        integration = Integration(user_id=current_user.id, platform=PLATFORM)
        db.add(integration)

    integration.access_token = session_key
    integration.platform_username = email
    integration.is_connected = True
    # Store encrypted credentials for re-auth
    integration.credentials = {"email": email, "password": password}
    db.commit()

    return {"status": "connected", "message": "Renpho connected successfully"}


@router.post("/disconnect")
async def disconnect_renpho(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    integration = _get_integration(current_user, db)
    if integration:
        integration.is_connected = False
        integration.access_token = None
        integration.credentials = None
        db.commit()
    return {"status": "disconnected"}


@router.post("/sync")
async def sync_renpho(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    days: int = Query(default=30, le=365)
):
    integration = _get_integration(current_user, db)
    if not integration or not integration.is_connected:
        raise HTTPException(status_code=400, detail="Renpho not connected")

    log = SyncLog(integration_id=integration.id)
    db.add(log)
    db.commit()

    synced = 0
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            RENPHO_MEASURE_URL,
            json={
                "terminal_user_session_key": integration.access_token,
                "last_at": (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S"),
                "offset": 0,
            },
            headers={"Content-Type": "application/json"},
        )

        if resp.status_code == 401:
            # Re-authenticate
            if integration.credentials:
                auth_resp = await client.post(
                    RENPHO_AUTH_URL,
                    json={
                        "email": integration.credentials.get("email"),
                        "password": integration.credentials.get("password"),
                        "terminal_user_session_key": "",
                    },
                )
                if auth_resp.status_code == 200:
                    auth_data = auth_resp.json()
                    integration.access_token = auth_data.get("terminal_user_session_key")
                    db.commit()
                    # Retry with new token
                    resp = await client.post(
                        RENPHO_MEASURE_URL,
                        json={
                            "terminal_user_session_key": integration.access_token,
                            "last_at": (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S"),
                            "offset": 0,
                        },
                    )

        if resp.status_code == 200:
            measurements = resp.json().get("scale_users", []) or resp.json().get("measurements", [])
            for m in measurements:
                time_str = m.get("time_stamp") or m.get("created_at")
                if not time_str:
                    continue
                try:
                    measured_at = datetime.fromisoformat(time_str.replace("Z", "+00:00"))
                except Exception:
                    continue

                body = BodyMetric(
                    user_id=current_user.id,
                    source=PLATFORM,
                    measured_at=measured_at,
                    weight_kg=float(m.get("weight", 0) or 0) or None,
                    bmi=float(m.get("bmi", 0) or 0) or None,
                    body_fat_percent=float(m.get("bodyfat", 0) or 0) or None,
                    muscle_mass_kg=float(m.get("muscle", 0) or 0) or None,
                    bone_mass_kg=float(m.get("bone", 0) or 0) or None,
                    water_percent=float(m.get("water", 0) or 0) or None,
                    visceral_fat=float(m.get("visceral_fat", 0) or 0) or None,
                    metabolic_age=int(float(m.get("body_age", 0) or 0)) or None,
                    basal_metabolic_rate=int(float(m.get("bmr", 0) or 0)) or None,
                    raw_data=m,
                )
                db.add(body)
                synced += 1

    integration.last_synced_at = datetime.now(timezone.utc)
    log.status = "success"
    log.records_synced = synced
    log.completed_at = datetime.now(timezone.utc)
    db.commit()
    return {"status": "success", "records_synced": synced}


@router.post("/import")
async def import_renpho_csv(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Import Renpho CSV export.
    In the Renpho app: Profile > More > Export data
    """
    content = await file.read()

    integration = _get_integration(current_user, db)
    if not integration:
        integration = Integration(user_id=current_user.id, platform=PLATFORM, is_connected=True)
        db.add(integration)
        db.commit()

    synced = 0
    reader = csv.DictReader(io.StringIO(content.decode("utf-8")))
    for row in reader:
        time_str = row.get("Time Stamp") or row.get("Date") or row.get("time_stamp")
        if not time_str:
            continue
        try:
            measured_at = datetime.fromisoformat(time_str.replace("Z", "+00:00"))
        except Exception:
            try:
                measured_at = datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S")
            except Exception:
                continue

        def parse_float(key):
            val = row.get(key)
            try:
                return float(val) if val else None
            except Exception:
                return None

        body = BodyMetric(
            user_id=current_user.id,
            source=PLATFORM,
            measured_at=measured_at.replace(tzinfo=timezone.utc) if measured_at.tzinfo is None else measured_at,
            weight_kg=parse_float("Weight(kg)") or parse_float("Weight"),
            bmi=parse_float("BMI"),
            body_fat_percent=parse_float("Body Fat(%)") or parse_float("Body Fat"),
            muscle_mass_kg=parse_float("Muscle Mass(kg)") or parse_float("Muscle Mass"),
            bone_mass_kg=parse_float("Bone Mass(kg)") or parse_float("Bone Mass"),
            water_percent=parse_float("Water(%)") or parse_float("Water"),
            visceral_fat=parse_float("Visceral Fat"),
            metabolic_age=int(parse_float("Body Age") or 0) or None,
            basal_metabolic_rate=int(parse_float("BMR(kcal)") or parse_float("BMR") or 0) or None,
            raw_data=dict(row),
        )
        db.add(body)
        synced += 1

    integration.last_synced_at = datetime.now(timezone.utc)
    db.commit()
    return {"status": "success", "records_imported": synced}
