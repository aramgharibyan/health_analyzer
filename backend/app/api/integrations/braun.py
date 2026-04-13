"""
Braun Health Devices Integration
Braun makes blood pressure monitors, thermometers, ear thermometers.
Most sync via Braun HealthyHeart app which connects to Apple HealthKit / Google Fit.
This integration supports:
1. Direct Braun API (if partner access granted)
2. CSV export import from Braun HealthyHeart app
3. Manual entry for one-off readings
"""
from datetime import datetime, timezone
from typing import Optional
import httpx
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Body
from sqlalchemy.orm import Session
import csv, io

from app.database import get_db
from app.models.integration import Integration, SyncLog
from app.models.health_data import BodyMetric
from app.api.auth import get_current_user
from app.models.user import User
from app.config import get_settings

router = APIRouter(prefix="/braun")
settings = get_settings()
PLATFORM = "braun"

BRAUN_API_BASE = "https://api.braunhealthcare.com/v1"


def _get_integration(user: User, db: Session) -> Optional[Integration]:
    return db.query(Integration).filter_by(user_id=user.id, platform=PLATFORM).first()


@router.post("/connect")
async def connect_braun(
    api_key: str = Body(..., embed=True),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Connect Braun via API key (obtained from Braun partner portal).
    For consumer devices: use the import endpoint instead.
    """
    # Verify the API key
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{BRAUN_API_BASE}/user/profile",
            headers={"X-API-Key": api_key},
        )

    if resp.status_code not in (200, 404):  # 404 = valid key, no user found
        raise HTTPException(status_code=401, detail="Invalid Braun API key")

    integration = _get_integration(current_user, db)
    if not integration:
        integration = Integration(user_id=current_user.id, platform=PLATFORM)
        db.add(integration)

    integration.access_token = api_key
    integration.is_connected = True
    db.commit()

    return {"status": "connected"}


@router.post("/disconnect")
async def disconnect_braun(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    integration = _get_integration(current_user, db)
    if integration:
        integration.is_connected = False
        integration.access_token = None
        db.commit()
    return {"status": "disconnected"}


@router.post("/manual-entry")
async def add_manual_reading(
    systolic: int = Body(...),
    diastolic: int = Body(...),
    pulse: int = Body(None),
    measured_at: Optional[datetime] = Body(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Manually enter a blood pressure reading."""
    integration = _get_integration(current_user, db)
    if not integration:
        integration = Integration(user_id=current_user.id, platform=PLATFORM, is_connected=True)
        db.add(integration)
        db.commit()

    reading = BodyMetric(
        user_id=current_user.id,
        source=PLATFORM,
        measured_at=measured_at or datetime.now(timezone.utc),
        systolic_bp=systolic,
        diastolic_bp=diastolic,
        pulse=pulse,
    )
    db.add(reading)
    integration.last_synced_at = datetime.now(timezone.utc)
    db.commit()

    return {"status": "success", "reading_id": reading.id}


@router.post("/import")
async def import_braun_export(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Import Braun HealthyHeart CSV export.
    In the app: Menu > Data Export > CSV
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
        date_str = row.get("Date") or row.get("Datetime") or row.get("Measurement Date")
        if not date_str:
            continue
        try:
            measured_at = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
            if measured_at.tzinfo is None:
                measured_at = measured_at.replace(tzinfo=timezone.utc)
        except Exception:
            continue

        def parse_int(key):
            val = row.get(key)
            try:
                return int(float(val)) if val else None
            except Exception:
                return None

        reading = BodyMetric(
            user_id=current_user.id,
            source=PLATFORM,
            measured_at=measured_at,
            systolic_bp=parse_int("Systolic") or parse_int("SYS") or parse_int("Systolic (mmHg)"),
            diastolic_bp=parse_int("Diastolic") or parse_int("DIA") or parse_int("Diastolic (mmHg)"),
            pulse=parse_int("Pulse") or parse_int("Heart Rate") or parse_int("Pulse (bpm)"),
            raw_data=dict(row),
        )
        db.add(reading)
        synced += 1

    integration.last_synced_at = datetime.now(timezone.utc)
    db.commit()
    return {"status": "success", "records_imported": synced}
