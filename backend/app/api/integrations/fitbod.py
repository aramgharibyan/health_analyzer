"""
Fitbod Integration
Fitbod provides workout tracking. Uses OAuth2 for API access.
Provides: strength workouts, sets, reps, volume, muscle group targeting
"""
from datetime import datetime, timezone, timedelta
from typing import Optional
import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
import json

from app.database import get_db
from app.models.integration import Integration, SyncLog
from app.models.health_data import ActivityRecord
from app.api.auth import get_current_user
from app.models.user import User
from app.config import get_settings

router = APIRouter(prefix="/fitbod")
settings = get_settings()
PLATFORM = "fitbod"

FITBOD_AUTH_URL = "https://fitbod.me/oauth/authorize"
FITBOD_TOKEN_URL = "https://fitbod.me/oauth/token"
FITBOD_API_BASE = "https://api.fitbod.me/api/v1"


def _get_integration(user: User, db: Session) -> Optional[Integration]:
    return db.query(Integration).filter_by(user_id=user.id, platform=PLATFORM).first()


@router.get("/connect")
async def connect_fitbod(
    mobile: bool = False,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    integration = _get_integration(current_user, db)
    if not integration:
        integration = Integration(user_id=current_user.id, platform=PLATFORM)
        db.add(integration)
        db.commit()

    redirect_uri = settings.fitbod_mobile_redirect_uri if mobile else settings.fitbod_redirect_uri
    params = {
        "response_type": "code",
        "client_id": settings.fitbod_client_id,
        "redirect_uri": redirect_uri,
        "scope": "workouts:read",
        "state": str(current_user.id),
    }
    query = "&".join(f"{k}={v}" for k, v in params.items())
    return {"auth_url": f"{FITBOD_AUTH_URL}?{query}"}


@router.get("/callback")
async def fitbod_callback(
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
            FITBOD_TOKEN_URL,
            data={
                "grant_type": "authorization_code",
                "client_id": settings.fitbod_client_id,
                "client_secret": settings.fitbod_client_secret,
                "code": code,
                "redirect_uri": settings.fitbod_redirect_uri,
            },
        )
    if resp.status_code != 200:
        raise HTTPException(status_code=400, detail=f"Token exchange failed: {resp.text}")

    token_data = resp.json()
    integration.access_token = token_data["access_token"]
    integration.refresh_token = token_data.get("refresh_token")
    if token_data.get("expires_in"):
        integration.token_expires_at = datetime.now(timezone.utc) + timedelta(
            seconds=token_data["expires_in"]
        )
    integration.is_connected = True
    db.commit()

    return RedirectResponse(f"{settings.frontend_url}/integrations?connected=fitbod")


@router.post("/disconnect")
async def disconnect_fitbod(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    integration = _get_integration(current_user, db)
    if integration:
        integration.is_connected = False
        integration.access_token = None
        db.commit()
    return {"status": "disconnected"}


@router.post("/sync")
async def sync_fitbod(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    days: int = Query(default=30, le=365)
):
    integration = _get_integration(current_user, db)
    if not integration or not integration.is_connected:
        raise HTTPException(status_code=400, detail="Fitbod not connected")

    log = SyncLog(integration_id=integration.id)
    db.add(log)
    db.commit()

    synced = 0
    headers = {"Authorization": f"Bearer {integration.access_token}"}
    start = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(
            f"{FITBOD_API_BASE}/workouts",
            headers=headers,
            params={"start_date": start},
        )
        if resp.status_code == 200:
            for workout in resp.json().get("workouts", []):
                existing = db.query(ActivityRecord).filter_by(
                    user_id=current_user.id,
                    external_id=str(workout.get("id")),
                    source=PLATFORM
                ).first()
                if not existing:
                    exercises = workout.get("exercises", [])
                    total_volume = sum(
                        ex.get("weight_kg", 0) * ex.get("reps", 0) * ex.get("sets", 0)
                        for ex in exercises
                    )
                    activity = ActivityRecord(
                        user_id=current_user.id,
                        source=PLATFORM,
                        external_id=str(workout.get("id")),
                        activity_type="strength",
                        workout_name=workout.get("name", "Workout"),
                        start_time=datetime.fromisoformat(workout["date"]),
                        duration_minutes=workout.get("duration_minutes"),
                        calories_burned=workout.get("calories"),
                        sets_completed=sum(ex.get("sets", 0) for ex in exercises),
                        total_volume_kg=total_volume,
                        raw_data=workout,
                    )
                    db.add(activity)
                    synced += 1

    integration.last_synced_at = datetime.now(timezone.utc)
    log.status = "success"
    log.records_synced = synced
    log.completed_at = datetime.now(timezone.utc)
    db.commit()

    return {"status": "success", "records_synced": synced}


@router.post("/import")
async def import_fitbod_csv(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Import Fitbod workout export CSV/JSON (Settings > Export Workout Data)."""
    content = await file.read()

    integration = _get_integration(current_user, db)
    if not integration:
        integration = Integration(user_id=current_user.id, platform=PLATFORM, is_connected=True)
        db.add(integration)
        db.commit()

    synced = 0
    if file.filename.endswith(".json"):
        workouts = json.loads(content)
    else:
        # CSV parsing
        import csv, io
        reader = csv.DictReader(io.StringIO(content.decode("utf-8")))
        workouts = list(reader)

    for w in workouts:
        date_str = w.get("Date") or w.get("date") or w.get("workout_date")
        if not date_str:
            continue
        try:
            start_time = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        except Exception:
            continue

        activity = ActivityRecord(
            user_id=current_user.id,
            source=PLATFORM,
            activity_type="strength",
            workout_name=w.get("Exercise") or w.get("name", "Workout"),
            start_time=start_time,
            duration_minutes=int(w.get("Duration", 0) or 0),
            calories_burned=float(w.get("Calories", 0) or 0),
            total_volume_kg=float(w.get("Volume", 0) or 0),
            raw_data=w,
        )
        db.add(activity)
        synced += 1

    integration.last_synced_at = datetime.now(timezone.utc)
    db.commit()
    return {"status": "success", "records_imported": synced}
