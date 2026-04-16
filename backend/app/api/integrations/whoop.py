"""
Whoop API Integration
Docs: https://developer.whoop.com/api
OAuth2 with PKCE flow.
Provides: sleep, recovery, strain, body measurements
"""
import secrets
import hashlib
import base64
from datetime import datetime, timezone, timedelta
from typing import Optional
import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.integration import Integration, SyncLog
from app.models.health_data import SleepRecord, ActivityRecord, BodyMetric
from app.api.auth import get_current_user
from app.models.user import User
from app.config import get_settings

router = APIRouter(prefix="/whoop")
settings = get_settings()

PLATFORM = "whoop"
SCOPES = "offline read:sleep read:recovery read:cycles read:workout read:body_measurement read:profile"


def _get_integration(user: User, db: Session) -> Optional[Integration]:
    return db.query(Integration).filter_by(user_id=user.id, platform=PLATFORM).first()


def _save_tokens(integration: Integration, token_data: dict, db: Session):
    integration.access_token = token_data["access_token"]
    integration.refresh_token = token_data.get("refresh_token")
    integration.token_scope = token_data.get("scope")
    if token_data.get("expires_in"):
        integration.token_expires_at = datetime.now(timezone.utc) + timedelta(
            seconds=token_data["expires_in"]
        )
    integration.is_connected = True
    db.commit()


async def _refresh_token_if_needed(integration: Integration, db: Session):
    if not integration.token_expires_at:
        return
    if datetime.now(timezone.utc) < integration.token_expires_at - timedelta(minutes=5):
        return
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            settings.whoop_token_url,
            data={
                "grant_type": "refresh_token",
                "refresh_token": integration.refresh_token,
                "client_id": settings.whoop_client_id,
                "client_secret": settings.whoop_client_secret,
            },
        )
        if resp.status_code == 200:
            _save_tokens(integration, resp.json(), db)


@router.get("/connect")
async def connect_whoop(
    mobile: bool = False,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Start Whoop OAuth2 PKCE flow. Pass ?mobile=true from the mobile app."""
    code_verifier = secrets.token_urlsafe(64)
    code_challenge = base64.urlsafe_b64encode(
        hashlib.sha256(code_verifier.encode()).digest()
    ).rstrip(b"=").decode()

    redirect_uri = settings.whoop_mobile_redirect_uri if mobile else settings.whoop_redirect_uri

    # Store verifier in integration record for callback
    integration = _get_integration(current_user, db)
    if not integration:
        integration = Integration(user_id=current_user.id, platform=PLATFORM)
        db.add(integration)
    integration.credentials = {"code_verifier": code_verifier}
    db.commit()

    params = {
        "client_id": settings.whoop_client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": SCOPES,
        "state": str(current_user.id),
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
    }
    query = "&".join(f"{k}={v}" for k, v in params.items())
    auth_url = f"{settings.whoop_auth_url}?{query}"
    return {"auth_url": auth_url}


@router.get("/callback")
async def whoop_callback(
    code: str = Query(...),
    state: str = Query(...),
    db: Session = Depends(get_db)
):
    """Handle Whoop OAuth callback."""
    user_id = int(state)
    integration = db.query(Integration).filter_by(user_id=user_id, platform=PLATFORM).first()
    if not integration or not integration.credentials:
        raise HTTPException(status_code=400, detail="Invalid OAuth state")

    code_verifier = integration.credentials.get("code_verifier")
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            settings.whoop_token_url,
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": settings.whoop_redirect_uri,
                "client_id": settings.whoop_client_id,
                "client_secret": settings.whoop_client_secret,
                "code_verifier": code_verifier,
            },
        )
    if resp.status_code != 200:
        raise HTTPException(status_code=400, detail=f"Token exchange failed: {resp.text}")

    _save_tokens(integration, resp.json(), db)

    # Fetch user profile
    async with httpx.AsyncClient() as client:
        profile_resp = await client.get(
            f"{settings.whoop_api_base}/user/profile/basic",
            headers={"Authorization": f"Bearer {integration.access_token}"},
        )
    if profile_resp.status_code == 200:
        profile = profile_resp.json()
        integration.platform_user_id = str(profile.get("user_id", ""))
        integration.platform_username = profile.get("email", "")
        db.commit()

    return RedirectResponse(f"{settings.frontend_url}/integrations?connected=whoop")


@router.post("/disconnect")
async def disconnect_whoop(
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


@router.post("/sync")
async def sync_whoop(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    days: int = Query(default=30, le=365)
):
    """Sync data from Whoop API."""
    integration = _get_integration(current_user, db)
    if not integration or not integration.is_connected:
        raise HTTPException(status_code=400, detail="Whoop not connected")

    await _refresh_token_if_needed(integration, db)

    log = SyncLog(integration_id=integration.id)
    db.add(log)
    db.commit()

    synced = 0
    headers = {"Authorization": f"Bearer {integration.access_token}"}
    start = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()

    async with httpx.AsyncClient(timeout=30) as client:
        # Sync sleep records
        resp = await client.get(
            f"{settings.whoop_api_base}/activity/sleep",
            headers=headers,
            params={"start": start, "limit": 25},
        )
        if resp.status_code == 200:
            for record in resp.json().get("records", []):
                existing = db.query(SleepRecord).filter_by(
                    user_id=current_user.id,
                    external_id=str(record["id"]),
                    source=PLATFORM
                ).first()
                if not existing:
                    stage = record.get("stage_summary", {})
                    score = record.get("score", {})
                    sleep = SleepRecord(
                        user_id=current_user.id,
                        source=PLATFORM,
                        external_id=str(record["id"]),
                        start_time=datetime.fromisoformat(record["start"].replace("Z", "+00:00")),
                        end_time=datetime.fromisoformat(record["end"].replace("Z", "+00:00")),
                        total_duration_minutes=int(stage.get("total_in_bed_time_milli", 0) / 60000),
                        sleep_efficiency=score.get("sleep_efficiency_percentage"),
                        deep_sleep_minutes=int(stage.get("total_slow_wave_sleep_time_milli", 0) / 60000),
                        light_sleep_minutes=int(stage.get("total_light_sleep_time_milli", 0) / 60000),
                        rem_sleep_minutes=int(stage.get("total_rem_sleep_time_milli", 0) / 60000),
                        awake_minutes=int(stage.get("total_awake_time_milli", 0) / 60000),
                        sleep_score=score.get("stage_summary", {}).get("sleep_score"),
                        recovery_score=record.get("score", {}).get("recovery_score"),
                        hrv=score.get("hrv_rmssd_milli"),
                        avg_spo2=score.get("avg_oxygen_saturation"),
                        respiratory_rate=score.get("respiratory_rate"),
                        raw_data=record,
                    )
                    db.add(sleep)
                    synced += 1

        # Sync workouts / strain
        resp = await client.get(
            f"{settings.whoop_api_base}/activity/workout",
            headers=headers,
            params={"start": start, "limit": 25},
        )
        if resp.status_code == 200:
            for record in resp.json().get("records", []):
                existing = db.query(ActivityRecord).filter_by(
                    user_id=current_user.id,
                    external_id=str(record["id"]),
                    source=PLATFORM
                ).first()
                if not existing:
                    score = record.get("score", {})
                    activity = ActivityRecord(
                        user_id=current_user.id,
                        source=PLATFORM,
                        external_id=str(record["id"]),
                        activity_type=record.get("sport_id", "unknown"),
                        start_time=datetime.fromisoformat(record["start"].replace("Z", "+00:00")),
                        end_time=datetime.fromisoformat(record["end"].replace("Z", "+00:00")),
                        calories_burned=score.get("kilojoule", 0) * 0.239006,
                        avg_heart_rate=score.get("average_heart_rate"),
                        max_heart_rate=score.get("max_heart_rate"),
                        strain_score=score.get("strain"),
                        raw_data=record,
                    )
                    db.add(activity)
                    synced += 1

        # Sync body measurements
        resp = await client.get(
            f"{settings.whoop_api_base}/user/measurement/body",
            headers=headers,
        )
        if resp.status_code == 200:
            data = resp.json()
            if data:
                body = BodyMetric(
                    user_id=current_user.id,
                    source=PLATFORM,
                    measured_at=datetime.now(timezone.utc),
                    weight_kg=data.get("weight_kilogram"),
                    height_cm=data.get("height_meter", 0) * 100 if data.get("height_meter") else None,
                    raw_data=data,
                )
                db.add(body)
                synced += 1

    integration.last_synced_at = datetime.now(timezone.utc)
    log.status = "success"
    log.records_synced = synced
    log.completed_at = datetime.now(timezone.utc)
    db.commit()

    return {"status": "success", "records_synced": synced}
