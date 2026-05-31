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
from app.models.health_data import SleepRecord, ActivityRecord, BodyMetric, HealthMetric
from app.api.auth import get_current_user
from app.models.user import User
from app.config import get_settings

router = APIRouter(prefix="/whoop")
settings = get_settings()

PLATFORM = "whoop"
SCOPES = "offline read:sleep read:recovery read:cycles read:workout read:body_measurement read:profile"

# Whoop sport_id -> human-readable name (common subset; falls back to "sport_<id>")
WHOOP_SPORTS = {
    -1: "Activity", 0: "Running", 1: "Cycling", 16: "Baseball", 17: "Basketball",
    18: "Rowing", 19: "Fencing", 20: "Field Hockey", 21: "Football", 22: "Golf",
    24: "Ice Hockey", 25: "Lacrosse", 27: "Rugby", 28: "Sailing", 29: "Skiing",
    30: "Soccer", 31: "Softball", 32: "Squash", 33: "Swimming", 34: "Tennis",
    35: "Track & Field", 36: "Volleyball", 37: "Water Polo", 38: "Wrestling",
    39: "Boxing", 42: "Dance", 43: "Pilates", 44: "Yoga", 45: "Weightlifting",
    47: "Cross Country Skiing", 48: "Functional Fitness", 52: "Hiking/Rucking",
    55: "Kayaking", 56: "Martial Arts", 57: "Mountain Biking", 59: "Powerlifting",
    60: "Rock Climbing", 62: "Triathlon", 63: "Walking", 64: "Surfing",
    65: "Elliptical", 66: "Stairmaster", 70: "Meditation", 71: "Other",
    84: "Jumping Rope", 91: "Snowboarding", 96: "HIIT", 97: "Spin", 98: "Jiu Jitsu",
    101: "Pickleball", 107: "Barre", 126: "Assault Bike", 127: "Kickboxing",
    128: "Stretching", 230: "Table Tennis", 231: "Badminton",
}

KJ_TO_KCAL = 0.239006


def _sport_name(sport_id) -> str:
    try:
        return WHOOP_SPORTS.get(int(sport_id), f"sport_{sport_id}")
    except (TypeError, ValueError):
        return "unknown"


def _parse_dt(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


class WhoopAPIError(Exception):
    """Raised when a Whoop endpoint returns a non-200 so failures aren't silent."""

    def __init__(self, status: int, body: str):
        self.status = status
        self.body = body
        super().__init__(f"HTTP {status}: {body[:300]}")


async def _fetch_all(client, url, headers, params, max_pages: int = 30) -> list:
    """Page through a Whoop collection endpoint following next_token.

    Raises WhoopAPIError on a non-200 response so the caller can record and
    report it instead of silently returning an empty list (which previously
    made sleep/workout failures look like "no data").
    """
    records: list = []
    next_token = None
    for _ in range(max_pages):
        page_params = dict(params)
        if next_token:
            page_params["nextToken"] = next_token
        resp = await client.get(url, headers=headers, params=page_params)
        if resp.status_code != 200:
            raise WhoopAPIError(resp.status_code, resp.text)
        body = resp.json()
        records.extend(body.get("records", []))
        next_token = body.get("next_token")
        if not next_token:
            break
    return records


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

    token_expires_at = integration.token_expires_at
    if token_expires_at.tzinfo is None:
        token_expires_at = token_expires_at.replace(tzinfo=timezone.utc)

    if datetime.now(timezone.utc) < token_expires_at - timedelta(minutes=5):
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

    # Use a secure random state and preserve the user ID for callback lookup.
    state = f"{current_user.id}:{secrets.token_urlsafe(32)}"

    # Store verifier + state in integration record for callback validation.
    integration = _get_integration(current_user, db)
    if not integration:
        integration = Integration(user_id=current_user.id, platform=PLATFORM)
        db.add(integration)
    integration.credentials = {
        "code_verifier": code_verifier,
        "oauth_state": state,
    }
    db.commit()

    params = {
        "client_id": settings.whoop_client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": SCOPES,
        "state": state,
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
    if ":" not in state:
        raise HTTPException(status_code=400, detail="Invalid OAuth state")

    user_id_str, _ = state.split(":", 1)
    try:
        user_id = int(user_id_str)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid OAuth state")

    integration = db.query(Integration).filter_by(user_id=user_id, platform=PLATFORM).first()
    if not integration or not integration.credentials:
        raise HTTPException(status_code=400, detail="Invalid OAuth state")

    expected_state = integration.credentials.get("oauth_state")
    if expected_state != state:
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

    user = db.query(User).filter_by(id=user_id).first()
    if user:
        try:
            await sync_whoop(user, db)
        except Exception:
            # Sync is best-effort on initial connect; connection still succeeds.
            pass

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
    errors: dict[str, dict] = {}
    counts: dict[str, int] = {}
    headers = {"Authorization": f"Bearer {integration.access_token}"}
    start = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    base = settings.whoop_api_base
    params = {"start": start, "limit": 25}

    async with httpx.AsyncClient(timeout=30) as client:
        async def fetch(resource: str, path: str) -> list:
            """Fetch a collection, recording failures instead of swallowing them."""
            try:
                records = await _fetch_all(client, f"{base}/{path}", headers, params)
                counts[resource] = len(records)
                return records
            except WhoopAPIError as exc:
                errors[resource] = {"status": exc.status, "body": exc.body[:500]}
            except Exception as exc:  # network, parsing, etc.
                errors[resource] = {"error": str(exc)}
            return []

        # 1. Recovery first — keyed by sleep_id so we can enrich each sleep record
        #    with HRV, recovery score, resting HR and SpO2 (Whoop's core metrics).
        recovery_by_sleep: dict[str, dict] = {}
        for record in await fetch("recovery", "recovery"):
            if record.get("score_state") != "SCORED":
                continue
            score = record.get("score") or {}
            sleep_id = record.get("sleep_id")
            if sleep_id is not None:
                recovery_by_sleep[str(sleep_id)] = score

        # 2. Sleep — fix stage nesting (score.stage_summary) and merge recovery in.
        for record in await fetch("sleep", "activity/sleep"):
            if record.get("nap"):
                continue  # skip naps so the dashboard trend reflects main sleep
            score = record.get("score") or {}
            stage = score.get("stage_summary") or {}
            rec = recovery_by_sleep.get(str(record["id"]), {})

            fields = dict(
                start_time=_parse_dt(record["start"]),
                end_time=_parse_dt(record["end"]),
                total_duration_minutes=int(stage.get("total_in_bed_time_milli", 0) / 60000),
                sleep_efficiency=score.get("sleep_efficiency_percentage"),
                deep_sleep_minutes=int(stage.get("total_slow_wave_sleep_time_milli", 0) / 60000),
                light_sleep_minutes=int(stage.get("total_light_sleep_time_milli", 0) / 60000),
                rem_sleep_minutes=int(stage.get("total_rem_sleep_time_milli", 0) / 60000),
                awake_minutes=int(stage.get("total_awake_time_milli", 0) / 60000),
                sleep_score=score.get("sleep_performance_percentage"),
                respiratory_rate=score.get("respiratory_rate"),
                # enriched from /recovery
                recovery_score=rec.get("recovery_score"),
                hrv=rec.get("hrv_rmssd_milli"),
                min_heart_rate=rec.get("resting_heart_rate"),
                avg_spo2=rec.get("spo2_percentage"),
                raw_data={"sleep": record, "recovery": rec or None},
            )

            existing = db.query(SleepRecord).filter_by(
                user_id=current_user.id, external_id=str(record["id"]), source=PLATFORM
            ).first()
            if existing:
                for k, v in fields.items():
                    setattr(existing, k, v)
            else:
                db.add(SleepRecord(
                    user_id=current_user.id, source=PLATFORM,
                    external_id=str(record["id"]), **fields,
                ))
            synced += 1

        # 3. Workouts / strain — with duration, distance and sport name.
        for record in await fetch("workout", "activity/workout"):
            score = record.get("score") or {}
            start_t = _parse_dt(record["start"])
            end_t = _parse_dt(record["end"])
            distance_m = score.get("distance_meter")
            fields = dict(
                activity_type=_sport_name(record.get("sport_id")),
                workout_name=_sport_name(record.get("sport_id")),
                start_time=start_t,
                end_time=end_t,
                duration_minutes=int((end_t - start_t).total_seconds() / 60),
                calories_burned=(score.get("kilojoule") or 0) * KJ_TO_KCAL or None,
                avg_heart_rate=score.get("average_heart_rate"),
                max_heart_rate=score.get("max_heart_rate"),
                strain_score=score.get("strain"),
                distance_km=distance_m / 1000 if distance_m else None,
                raw_data=record,
            )
            existing = db.query(ActivityRecord).filter_by(
                user_id=current_user.id, external_id=str(record["id"]), source=PLATFORM
            ).first()
            if existing:
                for k, v in fields.items():
                    setattr(existing, k, v)
            else:
                db.add(ActivityRecord(
                    user_id=current_user.id, source=PLATFORM,
                    external_id=str(record["id"]), **fields,
                ))
            synced += 1

        # 4. Physiological cycles — daily strain, calories, avg/max HR.
        #    Stored as generic HealthMetric rows so they don't pollute workouts.
        for record in await fetch("cycle", "cycle"):
            score = record.get("score") or {}
            if record.get("score_state") != "SCORED":
                continue
            cycle_start = _parse_dt(record["start"])
            cycle_metrics = {
                "day_strain": (score.get("strain"), "strain"),
                "day_calories": ((score.get("kilojoule") or 0) * KJ_TO_KCAL or None, "kcal"),
                "day_avg_heart_rate": (score.get("average_heart_rate"), "bpm"),
                "day_max_heart_rate": (score.get("max_heart_rate"), "bpm"),
            }
            for metric_type, (value, unit) in cycle_metrics.items():
                if value is None:
                    continue
                existing = db.query(HealthMetric).filter_by(
                    user_id=current_user.id, source=PLATFORM,
                    metric_type=metric_type, recorded_at=cycle_start,
                ).first()
                if existing:
                    existing.value = value
                else:
                    db.add(HealthMetric(
                        user_id=current_user.id, source=PLATFORM,
                        metric_type=metric_type, value=value, unit=unit,
                        recorded_at=cycle_start, raw_data=record,
                    ))
                synced += 1

        # 5. Body measurement — keep a single up-to-date row instead of duplicating.
        #    (Height lives on the user profile, not on BodyMetric.)
        resp = await client.get(f"{base}/user/measurement/body", headers=headers)
        if resp.status_code == 200 and resp.json():
            data = resp.json()
            counts["body"] = 1
            if data.get("height_meter") and not current_user.height_cm:
                current_user.height_cm = data["height_meter"] * 100
            body = (
                db.query(BodyMetric)
                .filter_by(user_id=current_user.id, source=PLATFORM)
                .order_by(BodyMetric.measured_at.desc())
                .first()
            )
            if body:
                body.measured_at = datetime.now(timezone.utc)
                body.weight_kg = data.get("weight_kilogram")
                body.raw_data = data
            else:
                db.add(BodyMetric(
                    user_id=current_user.id, source=PLATFORM,
                    measured_at=datetime.now(timezone.utc),
                    weight_kg=data.get("weight_kilogram"),
                    raw_data=data,
                ))
            synced += 1
        elif resp.status_code != 200:
            errors["body"] = {"status": resp.status_code, "body": resp.text[:500]}

    integration.last_synced_at = datetime.now(timezone.utc)
    log.records_synced = synced
    log.completed_at = datetime.now(timezone.utc)
    log.details = {"counts": counts, "errors": errors, "granted_scope": integration.token_scope}
    if errors:
        # Some endpoints failed (e.g. missing OAuth scopes) — surface it.
        log.status = "partial" if synced else "failed"
        log.error_message = "; ".join(f"{k}: {v}" for k, v in errors.items())[:1000]
    else:
        log.status = "success"
    db.commit()

    return {
        "status": log.status,
        "records_synced": synced,
        "counts": counts,
        "errors": errors,
        "granted_scope": integration.token_scope,
    }
