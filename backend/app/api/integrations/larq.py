"""
Larq Smart Water Bottle Integration
Larq tracks hydration, UV purification cycles, and water temperature.
Uses OAuth2 via mylarq.com API.
Fallback: manual hydration tracking.
"""
from datetime import datetime, timezone, timedelta
from typing import Optional
import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.integration import Integration, SyncLog
from app.models.health_data import HydrationRecord
from app.api.auth import get_current_user
from app.models.user import User
from app.config import get_settings

router = APIRouter(prefix="/larq")
settings = get_settings()
PLATFORM = "larq"

LARQ_AUTH_URL = "https://account.mylarq.com/oauth/authorize"
LARQ_TOKEN_URL = "https://api.mylarq.com/oauth/token"


def _get_integration(user: User, db: Session) -> Optional[Integration]:
    return db.query(Integration).filter_by(user_id=user.id, platform=PLATFORM).first()


async def _refresh_token(integration: Integration, db: Session):
    if not integration.token_expires_at:
        return
    if datetime.now(timezone.utc) < integration.token_expires_at - timedelta(minutes=5):
        return
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            LARQ_TOKEN_URL,
            data={
                "grant_type": "refresh_token",
                "refresh_token": integration.refresh_token,
                "client_id": settings.larq_client_id,
                "client_secret": settings.larq_client_secret,
            },
        )
        if resp.status_code == 200:
            token_data = resp.json()
            integration.access_token = token_data.get("access_token")
            integration.refresh_token = token_data.get("refresh_token")
            if token_data.get("expires_in"):
                integration.token_expires_at = datetime.now(timezone.utc) + timedelta(
                    seconds=token_data["expires_in"]
                )
            db.commit()


@router.get("/connect")
async def connect_larq(
    mobile: bool = False,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    integration = _get_integration(current_user, db)
    if not integration:
        integration = Integration(user_id=current_user.id, platform=PLATFORM)
        db.add(integration)
        db.commit()

    redirect_uri = settings.larq_mobile_redirect_uri if mobile else settings.larq_redirect_uri
    params = {
        "client_id": settings.larq_client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "hydration.read",
        "state": str(current_user.id),
    }
    query = "&".join(f"{k}={v}" for k, v in params.items())
    return {"auth_url": f"{LARQ_AUTH_URL}?{query}"}


@router.get("/callback")
async def larq_callback(
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
            LARQ_TOKEN_URL,
            data={
                "grant_type": "authorization_code",
                "client_id": settings.larq_client_id,
                "client_secret": settings.larq_client_secret,
                "code": code,
                "redirect_uri": settings.larq_redirect_uri,
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

    return RedirectResponse(f"{settings.frontend_url}/integrations?connected=larq")


@router.post("/disconnect")
async def disconnect_larq(
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
async def sync_larq(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    days: int = Query(default=30, le=365)
):
    integration = _get_integration(current_user, db)
    if not integration or not integration.is_connected:
        raise HTTPException(status_code=400, detail="Larq not connected")

    await _refresh_token(integration, db)
    log = SyncLog(integration_id=integration.id)
    db.add(log)
    db.commit()

    synced = 0
    headers = {"Authorization": f"Bearer {integration.access_token}"}
    start = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(
            f"{settings.larq_api_base}/hydration",
            headers=headers,
            params={"start_date": start},
        )
        if resp.status_code == 200:
            for record in resp.json().get("hydration_logs", []):
                hydration = HydrationRecord(
                    user_id=current_user.id,
                    source=PLATFORM,
                    external_id=str(record.get("id", "")),
                    recorded_at=datetime.fromisoformat(record["timestamp"].replace("Z", "+00:00")),
                    amount_ml=record.get("amount_ml"),
                    daily_total_ml=record.get("daily_total_ml"),
                    daily_goal_ml=record.get("daily_goal_ml", 2000),
                    raw_data=record,
                )
                db.add(hydration)
                synced += 1

    integration.last_synced_at = datetime.now(timezone.utc)
    log.status = "success"
    log.records_synced = synced
    log.completed_at = datetime.now(timezone.utc)
    db.commit()
    return {"status": "success", "records_synced": synced}


@router.post("/log")
async def log_hydration(
    amount_ml: float = Body(...),
    recorded_at: Optional[datetime] = Body(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Manually log water intake."""
    integration = _get_integration(current_user, db)
    if not integration:
        integration = Integration(user_id=current_user.id, platform=PLATFORM, is_connected=True)
        db.add(integration)
        db.commit()

    record = HydrationRecord(
        user_id=current_user.id,
        source="manual",
        recorded_at=recorded_at or datetime.now(timezone.utc),
        amount_ml=amount_ml,
        daily_goal_ml=2000,
    )
    db.add(record)
    db.commit()
    return {"status": "success", "record_id": record.id}
