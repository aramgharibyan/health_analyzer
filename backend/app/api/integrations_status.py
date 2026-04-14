"""Endpoint to get status of all integrations for the current user."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.api.auth import get_current_user
from app.models.user import User
from app.models.integration import Integration
from app.schemas.integration import IntegrationStatus
from app.config import get_settings

router = APIRouter(prefix="/integrations", tags=["Integrations"])
settings = get_settings()

PLATFORMS = ["whoop", "withings", "fitbod", "yazio", "renpho", "braun", "larq", "apple_health"]

PLATFORM_META = {
    "whoop": {
        "name": "Whoop",
        "description": "Sleep, recovery, strain, and HRV tracking",
        "logo": "whoop",
        "auth_type": "oauth2",
        "data_types": ["sleep", "recovery", "activity", "hrv"],
    },
    "withings": {
        "name": "Withings",
        "description": "Smart scales, blood pressure, sleep tracking",
        "logo": "withings",
        "auth_type": "oauth2",
        "data_types": ["body_metrics", "blood_pressure", "sleep", "activity"],
    },
    "fitbod": {
        "name": "Fitbod",
        "description": "Personalized strength training workouts",
        "logo": "fitbod",
        "auth_type": "oauth2",
        "data_types": ["workouts", "strength", "volume"],
    },
    "yazio": {
        "name": "Yazio",
        "description": "Calorie tracking, nutrition, and meal planning",
        "logo": "yazio",
        "auth_type": "oauth2",
        "data_types": ["nutrition", "calories", "macros", "hydration"],
    },
    "renpho": {
        "name": "Renpho",
        "description": "Smart scale body composition tracking",
        "logo": "renpho",
        "auth_type": "credentials",
        "data_types": ["body_metrics", "weight", "body_fat", "muscle_mass"],
    },
    "braun": {
        "name": "Braun",
        "description": "Blood pressure monitors and health devices",
        "logo": "braun",
        "auth_type": "api_key",
        "data_types": ["blood_pressure", "pulse"],
    },
    "larq": {
        "name": "Larq",
        "description": "Smart water bottle hydration tracking",
        "logo": "larq",
        "auth_type": "oauth2",
        "data_types": ["hydration"],
    },
    "apple_health": {
        "name": "Apple Health",
        "description": "All HealthKit data: steps, sleep, heart rate, workouts, nutrition, body metrics",
        "logo": "apple_health",
        "auth_type": "export",
        "data_types": ["sleep", "activity", "heart_rate", "hrv", "nutrition", "body_metrics", "hydration", "workouts"],
    },
}


@router.get("/status", response_model=List[dict])
def get_all_integration_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    integrations = {
        i.platform: i
        for i in db.query(Integration).filter_by(user_id=current_user.id).all()
    }

    result = []
    for platform in PLATFORMS:
        integration = integrations.get(platform)
        meta = PLATFORM_META.get(platform, {})

        status = {
            "platform": platform,
            "name": meta.get("name", platform.title()),
            "description": meta.get("description", ""),
            "auth_type": meta.get("auth_type", "oauth2"),
            "data_types": meta.get("data_types", []),
            "is_connected": integration.is_connected if integration else False,
            "is_active": integration.is_active if integration else False,
            "platform_username": integration.platform_username if integration else None,
            "last_synced_at": integration.last_synced_at.isoformat() if integration and integration.last_synced_at else None,
            "auto_sync": integration.auto_sync if integration else True,
        }
        result.append(status)

    return result


@router.post("/{platform}/toggle-auto-sync")
def toggle_auto_sync(
    platform: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    integration = db.query(Integration).filter_by(
        user_id=current_user.id, platform=platform
    ).first()
    if not integration:
        return {"error": "Integration not found"}

    integration.auto_sync = not integration.auto_sync
    db.commit()
    return {"platform": platform, "auto_sync": integration.auto_sync}


@router.post("/sync-all")
async def sync_all(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Trigger sync for all connected integrations (API-based only; Apple Health requires re-import)."""
    from app.api.integrations.whoop import sync_whoop
    from app.api.integrations.withings import sync_withings
    from app.api.integrations.fitbod import sync_fitbod
    from app.api.integrations.yazio import sync_yazio
    from app.api.integrations.renpho import sync_renpho
    from app.api.integrations.larq import sync_larq

    results = {}
    sync_fns = {
        "whoop": sync_whoop,
        "withings": sync_withings,
        "fitbod": sync_fitbod,
        "yazio": sync_yazio,
        "renpho": sync_renpho,
        "larq": sync_larq,
        # apple_health is export-based; skipped from auto-sync
    }

    integrations = db.query(Integration).filter_by(
        user_id=current_user.id, is_connected=True, auto_sync=True
    ).all()

    for integration in integrations:
        if integration.platform in sync_fns:
            try:
                result = await sync_fns[integration.platform](current_user, db)
                results[integration.platform] = result
            except Exception as e:
                results[integration.platform] = {"status": "error", "error": str(e)}

    return {"synced": results}
