"""
Yazio Nutrition API Integration
Yazio tracks food, calories, macros, water intake.
Uses OAuth2. Partner API access required for full data.
Fallback: CSV export import from Yazio app.
"""
from datetime import datetime, timezone, timedelta
from typing import Optional
import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
import csv, io, json

from app.database import get_db
from app.models.integration import Integration, SyncLog
from app.models.health_data import NutritionRecord, HydrationRecord
from app.api.auth import get_current_user
from app.models.user import User
from app.config import get_settings

router = APIRouter(prefix="/yazio")
settings = get_settings()
PLATFORM = "yazio"


def _get_integration(user: User, db: Session) -> Optional[Integration]:
    return db.query(Integration).filter_by(user_id=user.id, platform=PLATFORM).first()


async def _refresh_token(integration: Integration, db: Session):
    if not integration.token_expires_at:
        return
    if datetime.now(timezone.utc) < integration.token_expires_at - timedelta(minutes=5):
        return
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{settings.yazio_api_base}/oauth/token",
            data={
                "grant_type": "refresh_token",
                "refresh_token": integration.refresh_token,
                "client_id": settings.yazio_client_id,
                "client_secret": settings.yazio_client_secret,
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
async def connect_yazio(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    integration = _get_integration(current_user, db)
    if not integration:
        integration = Integration(user_id=current_user.id, platform=PLATFORM)
        db.add(integration)
        db.commit()

    params = {
        "client_id": settings.yazio_client_id,
        "redirect_uri": settings.yazio_redirect_uri,
        "response_type": "code",
        "scope": "food_diary water_intake",
        "state": str(current_user.id),
    }
    query = "&".join(f"{k}={v}" for k, v in params.items())
    return {"auth_url": f"{settings.yazio_api_base}/oauth/authorize?{query}"}


@router.get("/callback")
async def yazio_callback(
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
            f"{settings.yazio_api_base}/oauth/token",
            data={
                "grant_type": "authorization_code",
                "client_id": settings.yazio_client_id,
                "client_secret": settings.yazio_client_secret,
                "code": code,
                "redirect_uri": settings.yazio_redirect_uri,
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

    return RedirectResponse(f"{settings.frontend_url}/integrations?connected=yazio")


@router.post("/disconnect")
async def disconnect_yazio(
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
async def sync_yazio(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    days: int = Query(default=30, le=365)
):
    integration = _get_integration(current_user, db)
    if not integration or not integration.is_connected:
        raise HTTPException(status_code=400, detail="Yazio not connected")

    await _refresh_token(integration, db)
    log = SyncLog(integration_id=integration.id)
    db.add(log)
    db.commit()

    synced = 0
    headers = {"Authorization": f"Bearer {integration.access_token}"}

    async with httpx.AsyncClient(timeout=30) as client:
        for day_offset in range(days):
            date = (datetime.now() - timedelta(days=day_offset)).strftime("%Y-%m-%d")
            resp = await client.get(
                f"{settings.yazio_api_base}/diary/{date}",
                headers=headers,
            )
            if resp.status_code == 200:
                diary = resp.json()
                for meal in diary.get("meals", []):
                    nutrition = NutritionRecord(
                        user_id=current_user.id,
                        source=PLATFORM,
                        recorded_date=datetime.fromisoformat(date),
                        meal_type=meal.get("meal_type", "meal"),
                        calories=meal.get("calories"),
                        protein_g=meal.get("protein"),
                        carbs_g=meal.get("carbs"),
                        fat_g=meal.get("fat"),
                        fiber_g=meal.get("fiber"),
                        sugar_g=meal.get("sugar"),
                        food_items=meal.get("items", []),
                        raw_data=meal,
                    )
                    db.add(nutrition)
                    synced += 1

                # Hydration
                water_ml = diary.get("water_ml")
                if water_ml:
                    hydration = HydrationRecord(
                        user_id=current_user.id,
                        source=PLATFORM,
                        recorded_at=datetime.fromisoformat(date),
                        daily_total_ml=water_ml,
                        daily_goal_ml=diary.get("water_goal_ml"),
                    )
                    db.add(hydration)
                    synced += 1

    integration.last_synced_at = datetime.now(timezone.utc)
    log.status = "success"
    log.records_synced = synced
    log.completed_at = datetime.now(timezone.utc)
    db.commit()
    return {"status": "success", "records_synced": synced}


@router.post("/import")
async def import_yazio_export(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Import Yazio CSV export (Profile > Export Data)."""
    content = await file.read()

    integration = _get_integration(current_user, db)
    if not integration:
        integration = Integration(user_id=current_user.id, platform=PLATFORM, is_connected=True)
        db.add(integration)
        db.commit()

    synced = 0
    reader = csv.DictReader(io.StringIO(content.decode("utf-8")))
    for row in reader:
        try:
            date_str = row.get("Date") or row.get("date")
            if not date_str:
                continue
            nutrition = NutritionRecord(
                user_id=current_user.id,
                source=PLATFORM,
                recorded_date=datetime.fromisoformat(date_str),
                meal_type=row.get("Meal") or row.get("meal_type", "meal"),
                calories=float(row.get("Calories", 0) or 0),
                protein_g=float(row.get("Protein (g)", 0) or 0),
                carbs_g=float(row.get("Carbs (g)", 0) or 0),
                fat_g=float(row.get("Fat (g)", 0) or 0),
                fiber_g=float(row.get("Fiber (g)", 0) or 0),
                raw_data=dict(row),
            )
            db.add(nutrition)
            synced += 1
        except Exception:
            continue

    integration.last_synced_at = datetime.now(timezone.utc)
    db.commit()
    return {"status": "success", "records_imported": synced}
