"""
Apple Health Integration
========================
Apple HealthKit data is not accessible via a public web API — it lives on-device.
We support two ingestion methods:

1. EXPORT IMPORT (primary)
   In the iOS Health app: Profile icon → Export All Health Data → Share → upload the ZIP here.
   The ZIP contains export.xml which can be several hundred MB.
   We parse it with iterparse (streaming) so we never load the full file into memory.

2. WEBHOOK (real-time, via "Health Auto Export" iOS app)
   Install "Health Auto Export" on iPhone, point it at:
       POST /api/integrations/apple-health/webhook?token=<user_token>
   The app sends HealthKit batches as JSON on a schedule you configure.

Supported HealthKit types → our models:
  Steps, distance, active/basal calories        → ActivityRecord / HealthMetric
  Heart rate, resting HR, HRV                   → HealthMetric / SleepRecord.hrv
  Blood oxygen, respiratory rate                → HealthMetric / SleepRecord
  Body mass, BMI, body fat, lean mass           → BodyMetric
  Blood pressure (systolic / diastolic)         → BodyMetric
  Sleep analysis (in-bed, awake, core, deep, REM) → SleepRecord
  Dietary energy, protein, carbs, fat, fiber    → NutritionRecord
  Dietary water                                  → HydrationRecord
  Workouts (all activity types)                 → ActivityRecord
"""

import io
import os
import tempfile
import zipfile
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta, date
from collections import defaultdict
from typing import Optional, Union
import json

import aiofiles
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Request, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.api.auth import get_current_user
from app.models.user import User
from app.models.integration import Integration, SyncLog
from app.models.health_data import (
    SleepRecord, ActivityRecord, NutritionRecord,
    BodyMetric, HydrationRecord, HealthMetric,
)

router = APIRouter(prefix="/apple-health")
PLATFORM = "apple_health"

# ── Helpers ──────────────────────────────────────────────────────────────────

def _get_or_create_integration(user: User, db: Session) -> Integration:
    integration = db.query(Integration).filter_by(
        user_id=user.id, platform=PLATFORM
    ).first()
    if not integration:
        integration = Integration(
            user_id=user.id,
            platform=PLATFORM,
            is_connected=True,
            platform_username="Apple Health",
        )
        db.add(integration)
        db.commit()
        db.refresh(integration)
    return integration


def _parse_hk_date(s: str) -> Optional[datetime]:
    """Parse HealthKit date string '2024-01-15 10:30:00 -0800' → UTC datetime."""
    if not s:
        return None
    try:
        # Replace space before timezone offset with +/- for fromisoformat
        # '2024-01-15 10:30:00 -0800' → '2024-01-15T10:30:00-0800'
        s = s.strip()
        # split off timezone
        if " -" in s[10:] or " +" in s[10:]:
            idx = max(s.rfind(" -"), s.rfind(" +"))
            dt_part = s[:idx].replace(" ", "T")
            tz_part = s[idx+1:].replace(":", "")  # -0800
            if len(tz_part) == 5:   # -0800
                tz_part = tz_part[:3] + ":" + tz_part[3:]
            s = dt_part + tz_part
        return datetime.fromisoformat(s).astimezone(timezone.utc)
    except Exception:
        try:
            return datetime.strptime(s[:19], "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
        except Exception:
            return None


# ── HealthKit type → field mapping ───────────────────────────────────────────

# Types that map directly to a generic HealthMetric row
METRIC_TYPES: dict[str, tuple[str, str]] = {
    "HKQuantityTypeIdentifierStepCount":                   ("steps", "count"),
    "HKQuantityTypeIdentifierFlightsClimbed":              ("flights_climbed", "count"),
    "HKQuantityTypeIdentifierDistanceWalkingRunning":       ("distance_walking_running", "km"),
    "HKQuantityTypeIdentifierDistanceCycling":              ("distance_cycling", "km"),
    "HKQuantityTypeIdentifierHeartRate":                   ("heart_rate", "bpm"),
    "HKQuantityTypeIdentifierRestingHeartRate":             ("resting_heart_rate", "bpm"),
    "HKQuantityTypeIdentifierWalkingHeartRateAverage":      ("walking_heart_rate", "bpm"),
    "HKQuantityTypeIdentifierHeartRateVariabilitySDNN":     ("hrv", "ms"),
    "HKQuantityTypeIdentifierOxygenSaturation":             ("spo2", "%"),
    "HKQuantityTypeIdentifierRespiratoryRate":              ("respiratory_rate", "brpm"),
    "HKQuantityTypeIdentifierActiveEnergyBurned":          ("active_calories", "kcal"),
    "HKQuantityTypeIdentifierBasalEnergyBurned":           ("basal_calories", "kcal"),
    "HKQuantityTypeIdentifierVO2Max":                      ("vo2_max", "mL/kg/min"),
    "HKQuantityTypeIdentifierMindfulSession":               ("mindful_minutes", "min"),
    "HKQuantityTypeIdentifierAppleExerciseTime":           ("exercise_minutes", "min"),
    "HKQuantityTypeIdentifierAppleStandTime":              ("stand_minutes", "min"),
}

# Types we aggregate by day into NutritionRecord
NUTRITION_TYPES: dict[str, str] = {
    "HKQuantityTypeIdentifierDietaryEnergyConsumed": "calories",
    "HKQuantityTypeIdentifierDietaryProtein":        "protein_g",
    "HKQuantityTypeIdentifierDietaryCarbohydrates":  "carbs_g",
    "HKQuantityTypeIdentifierDietaryFatTotal":       "fat_g",
    "HKQuantityTypeIdentifierDietaryFiber":          "fiber_g",
    "HKQuantityTypeIdentifierDietarySugar":          "sugar_g",
    "HKQuantityTypeIdentifierDietarySodium":         "sodium_mg",
    "HKQuantityTypeIdentifierDietaryPotassium":      "potassium_mg",
    "HKQuantityTypeIdentifierDietaryCalcium":        "calcium_mg",
    "HKQuantityTypeIdentifierDietaryIron":           "iron_mg",
    "HKQuantityTypeIdentifierDietaryVitaminC":       "vitamin_c_mg",
    "HKQuantityTypeIdentifierDietaryVitaminD":       "vitamin_d_iu",
}

# Types we aggregate by day into BodyMetric
BODY_TYPES: dict[str, str] = {
    "HKQuantityTypeIdentifierBodyMass":              "weight_kg",
    "HKQuantityTypeIdentifierBodyMassIndex":         "bmi",
    "HKQuantityTypeIdentifierBodyFatPercentage":     "body_fat_percent",
    "HKQuantityTypeIdentifierLeanBodyMass":          "fat_free_mass_kg",
    "HKQuantityTypeIdentifierBloodPressureSystolic": "systolic_bp",
    "HKQuantityTypeIdentifierBloodPressureDiastolic":"diastolic_bp",
}

# Sleep category values
SLEEP_VALUE_MAP = {
    "HKCategoryValueSleepAnalysisInBed": "in_bed",
    "HKCategoryValueSleepAnalysisAsleep": "asleep_legacy",   # pre-iOS 16
    "HKCategoryValueSleepAnalysisAwake": "awake",
    "HKCategoryValueSleepAnalysisAsleepCore": "light",
    "HKCategoryValueSleepAnalysisAsleepDeep": "deep",
    "HKCategoryValueSleepAnalysisAsleepREM": "rem",
    # numeric aliases that appear in some exports
    "0": "in_bed",
    "1": "asleep_legacy",
    "2": "awake",
    "3": "light",
    "4": "deep",
    "5": "rem",
}

WORKOUT_TYPE_MAP = {
    "HKWorkoutActivityTypeRunning":              "running",
    "HKWorkoutActivityTypeCycling":              "cycling",
    "HKWorkoutActivityTypeWalking":              "walking",
    "HKWorkoutActivityTypeSwimming":             "swimming",
    "HKWorkoutActivityTypeHighIntensityIntervalTraining": "hiit",
    "HKWorkoutActivityTypeYoga":                 "yoga",
    "HKWorkoutActivityTypePilates":              "pilates",
    "HKWorkoutActivityTypeElliptical":           "elliptical",
    "HKWorkoutActivityTypeRowing":               "rowing",
    "HKWorkoutActivityTypeTraditionalStrengthTraining": "strength",
    "HKWorkoutActivityTypeFunctionalStrengthTraining":  "functional_strength",
    "HKWorkoutActivityTypeMixedCardio":          "mixed_cardio",
    "HKWorkoutActivityTypeCoreTraining":         "core",
    "HKWorkoutActivityTypeFlexibility":          "flexibility",
    "HKWorkoutActivityTypeStairClimbing":        "stair_climbing",
    "HKWorkoutActivityTypeHiking":               "hiking",
    "HKWorkoutActivityTypeSoccer":               "soccer",
    "HKWorkoutActivityTypeBasketball":           "basketball",
    "HKWorkoutActivityTypeTennis":               "tennis",
    "HKWorkoutActivityTypeOther":                "other",
}

# ── XML parsing ───────────────────────────────────────────────────────────────

class AppleHealthParser:
    """Streaming parser for Apple Health export.xml (iterparse to avoid OOM)."""

    def __init__(self):
        # daily buckets
        self.sleep_sessions: dict[str, dict] = {}  # date → {segments}
        self.nutrition_days: dict[str, dict] = defaultdict(lambda: defaultdict(float))
        self.body_days: dict[str, dict] = defaultdict(dict)
        self.hydration_days: dict[str, float] = defaultdict(float)
        self.metrics: list[dict] = []
        self.workouts: list[dict] = []

    def parse_file(self, source: Union[str, object]):
        """Parse XML from a file path or file-like object using iterparse (streaming, no OOM)."""
        ctx = ET.iterparse(source, events=("start", "end"))
        self._run_parse(ctx)

    def parse_stream(self, xml_bytes: bytes):
        """Parse XML bytes using iterparse (kept for small in-memory payloads)."""
        ctx = ET.iterparse(io.BytesIO(xml_bytes), events=("start", "end"))
        self._run_parse(ctx)

    def _run_parse(self, ctx):
        current_workout: Optional[dict] = None

        for event, elem in ctx:
            if event == "start":
                if elem.tag == "Workout":
                    current_workout = {
                        "type": elem.attrib.get("workoutActivityType", ""),
                        "start": elem.attrib.get("startDate", ""),
                        "end": elem.attrib.get("endDate", ""),
                        "duration_min": elem.attrib.get("duration"),
                        "duration_unit": elem.attrib.get("durationUnit", "min"),
                        "calories": None,
                        "distance_km": None,
                    }

            elif event == "end":
                tag = elem.tag

                if tag == "Record":
                    self._handle_record(elem)
                    elem.clear()

                elif tag == "WorkoutStatistics" and current_workout:
                    t = elem.attrib.get("type", "")
                    qty = elem.attrib.get("sum") or elem.attrib.get("average")
                    try:
                        qty = float(qty) if qty else None
                    except Exception:
                        qty = None
                    if "EnergyBurned" in t and qty:
                        current_workout["calories"] = qty
                    elif "Distance" in t and qty:
                        # convert to km if in meters
                        unit = elem.attrib.get("unit", "")
                        current_workout["distance_km"] = qty / 1000 if "m" == unit else qty

                elif tag == "Workout" and current_workout:
                    self.workouts.append(current_workout)
                    current_workout = None
                    elem.clear()

    def _handle_record(self, elem: ET.Element):
        rtype = elem.attrib.get("type", "")
        start = elem.attrib.get("startDate", "")
        end = elem.attrib.get("endDate", "")
        value_str = elem.attrib.get("value", "")
        unit = elem.attrib.get("unit", "")

        if not start:
            return

        start_dt = _parse_hk_date(start)
        if not start_dt:
            return
        day_key = start_dt.strftime("%Y-%m-%d")

        # ── Generic metrics ──
        if rtype in METRIC_TYPES:
            metric_name, default_unit = METRIC_TYPES[rtype]
            try:
                value = float(value_str)
                # unit conversions
                if metric_name in ("distance_walking_running", "distance_cycling"):
                    if unit in ("m", "mi"):
                        value = value / 1000 if unit == "m" else value * 1.60934
                elif metric_name == "spo2" and value <= 1.0:
                    value = value * 100  # 0-1 → 0-100%
                elif metric_name == "body_fat_percent" and value <= 1.0:
                    value = value * 100
                self.metrics.append({
                    "metric_type": metric_name,
                    "value": value,
                    "unit": default_unit,
                    "recorded_at": start_dt,
                })
            except (ValueError, TypeError):
                pass
            return

        # ── Nutrition ──
        if rtype in NUTRITION_TYPES:
            field = NUTRITION_TYPES[rtype]
            try:
                value = float(value_str)
                # convert mg sodium/potassium if expressed in g
                if field in ("sodium_mg", "potassium_mg", "calcium_mg", "iron_mg") and unit == "g":
                    value *= 1000
                elif field == "vitamin_d_iu" and unit == "mcg":
                    value *= 40  # mcg → IU approx
                self.nutrition_days[day_key][field] += value
                if "recorded_at" not in self.nutrition_days[day_key]:
                    self.nutrition_days[day_key]["recorded_at"] = start_dt
            except (ValueError, TypeError):
                pass
            return

        # ── Body metrics ──
        if rtype in BODY_TYPES:
            field = BODY_TYPES[rtype]
            try:
                value = float(value_str)
                if field == "weight_kg" and unit == "lb":
                    value *= 0.453592
                elif field == "body_fat_percent" and value <= 1.0:
                    value *= 100
                if field not in self.body_days[day_key]:
                    self.body_days[day_key][field] = value
                    self.body_days[day_key]["measured_at"] = start_dt
            except (ValueError, TypeError):
                pass
            return

        # ── Hydration ──
        if rtype == "HKQuantityTypeIdentifierDietaryWater":
            try:
                value = float(value_str)
                if unit == "L":
                    value *= 1000  # L → mL
                elif unit == "fl_oz":
                    value *= 29.5735
                self.hydration_days[day_key] += value
            except (ValueError, TypeError):
                pass
            return

        # ── Sleep analysis ──
        if rtype == "HKCategoryTypeIdentifierSleepAnalysis":
            end_dt = _parse_hk_date(end) or start_dt
            duration_min = max(0, int((end_dt - start_dt).total_seconds() / 60))
            stage = SLEEP_VALUE_MAP.get(value_str, "unknown")

            # Use the night's date (sleep starting after noon belongs to next-morning record)
            night_key = (start_dt - timedelta(hours=12)).strftime("%Y-%m-%d")

            if night_key not in self.sleep_sessions:
                self.sleep_sessions[night_key] = {
                    "start": start_dt,
                    "end": end_dt,
                    "in_bed": 0, "awake": 0, "light": 0, "deep": 0, "rem": 0,
                }
            sess = self.sleep_sessions[night_key]
            sess["start"] = min(sess["start"], start_dt)
            sess["end"] = max(sess["end"], end_dt)

            if stage == "in_bed":
                sess["in_bed"] += duration_min
            elif stage == "awake":
                sess["awake"] += duration_min
            elif stage in ("light", "asleep_legacy"):
                sess["light"] += duration_min
            elif stage == "deep":
                sess["deep"] += duration_min
            elif stage == "rem":
                sess["rem"] += duration_min


# ── Persistence ───────────────────────────────────────────────────────────────

def _persist_parsed(
    parser: AppleHealthParser,
    user_id: int,
    db: Session,
) -> int:
    synced = 0

    # Generic metrics (batch insert)
    for m in parser.metrics:
        row = HealthMetric(
            user_id=user_id,
            source=PLATFORM,
            metric_type=m["metric_type"],
            value=m["value"],
            unit=m["unit"],
            recorded_at=m["recorded_at"],
        )
        db.add(row)
        synced += 1

    # Nutrition by day
    for day_key, nutrients in parser.nutrition_days.items():
        recorded_at = nutrients.get("recorded_at") or datetime.strptime(day_key, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        nutrition = NutritionRecord(
            user_id=user_id,
            source=PLATFORM,
            recorded_date=recorded_at,
            meal_type="daily_total",
            calories=nutrients.get("calories"),
            protein_g=nutrients.get("protein_g"),
            carbs_g=nutrients.get("carbs_g"),
            fat_g=nutrients.get("fat_g"),
            fiber_g=nutrients.get("fiber_g"),
            sugar_g=nutrients.get("sugar_g"),
            sodium_mg=nutrients.get("sodium_mg"),
            potassium_mg=nutrients.get("potassium_mg"),
            calcium_mg=nutrients.get("calcium_mg"),
            iron_mg=nutrients.get("iron_mg"),
            vitamin_c_mg=nutrients.get("vitamin_c_mg"),
            vitamin_d_iu=nutrients.get("vitamin_d_iu"),
        )
        db.add(nutrition)
        synced += 1

    # Body metrics by day
    for day_key, body in parser.body_days.items():
        measured_at = body.get("measured_at") or datetime.strptime(day_key, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        bm = BodyMetric(
            user_id=user_id,
            source=PLATFORM,
            measured_at=measured_at,
            weight_kg=body.get("weight_kg"),
            bmi=body.get("bmi"),
            body_fat_percent=body.get("body_fat_percent"),
            fat_free_mass_kg=body.get("fat_free_mass_kg"),
            systolic_bp=int(body["systolic_bp"]) if body.get("systolic_bp") else None,
            diastolic_bp=int(body["diastolic_bp"]) if body.get("diastolic_bp") else None,
        )
        db.add(bm)
        synced += 1

    # Hydration by day
    for day_key, total_ml in parser.hydration_days.items():
        recorded_at = datetime.strptime(day_key, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        h = HydrationRecord(
            user_id=user_id,
            source=PLATFORM,
            recorded_at=recorded_at,
            daily_total_ml=total_ml,
            daily_goal_ml=2000,
        )
        db.add(h)
        synced += 1

    # Sleep sessions
    for night_key, sess in parser.sleep_sessions.items():
        total_sleep = sess["light"] + sess["deep"] + sess["rem"]
        total_in_bed = sess["in_bed"] or (total_sleep + sess["awake"])
        if total_in_bed == 0:
            continue
        efficiency = round((total_sleep / total_in_bed) * 100, 1) if total_in_bed > 0 else None
        sleep = SleepRecord(
            user_id=user_id,
            source=PLATFORM,
            external_id=f"apple_{night_key}",
            start_time=sess["start"],
            end_time=sess["end"],
            total_duration_minutes=total_in_bed,
            sleep_efficiency=efficiency,
            light_sleep_minutes=sess["light"],
            deep_sleep_minutes=sess["deep"],
            rem_sleep_minutes=sess["rem"],
            awake_minutes=sess["awake"],
        )
        db.add(sleep)
        synced += 1

    # Workouts
    for w in parser.workouts:
        start_dt = _parse_hk_date(w["start"])
        end_dt = _parse_hk_date(w["end"])
        if not start_dt:
            continue
        try:
            duration = float(w["duration_min"]) if w["duration_min"] else None
            if duration and w.get("duration_unit", "min") == "s":
                duration /= 60
        except (TypeError, ValueError):
            duration = None

        activity_type = WORKOUT_TYPE_MAP.get(w["type"], w["type"].replace("HKWorkoutActivityType", "").lower())
        activity = ActivityRecord(
            user_id=user_id,
            source=PLATFORM,
            activity_type=activity_type,
            workout_name=activity_type.replace("_", " ").title(),
            start_time=start_dt,
            end_time=end_dt,
            duration_minutes=int(duration) if duration else None,
            calories_burned=w.get("calories"),
            distance_km=w.get("distance_km"),
        )
        db.add(activity)
        synced += 1

    db.commit()
    return synced


# ── API endpoints ─────────────────────────────────────────────────────────────

@router.post("/import")
async def import_apple_health(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Upload the Apple Health ZIP export (or the raw export.xml).
    In the iOS Health app: tap your profile picture → Export All Health Data.
    The file is streamed to /tmp in 1 MB chunks to avoid OOM on 500 MB exports.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")

    fname = file.filename.lower()
    if not (fname.endswith(".zip") or fname.endswith(".xml")):
        raise HTTPException(
            status_code=400,
            detail="Please upload the export.zip from the Health app, or the export.xml file directly.",
        )

    # Stream the upload to /tmp (never load the full file into memory)
    suffix = ".zip" if fname.endswith(".zip") else ".xml"
    tmp_fd, tmp_path = tempfile.mkstemp(suffix=suffix, dir="/tmp")
    os.close(tmp_fd)

    try:
        async with aiofiles.open(tmp_path, "wb") as out:
            while True:
                chunk = await file.read(1024 * 1024)  # 1 MB at a time
                if not chunk:
                    break
                await out.write(chunk)

        integration = _get_or_create_integration(current_user, db)
        log = SyncLog(integration_id=integration.id)
        db.add(log)
        db.commit()

        try:
            parser = AppleHealthParser()

            if fname.endswith(".zip"):
                try:
                    with zipfile.ZipFile(tmp_path) as zf:
                        xml_name = next(
                            (n for n in zf.namelist() if n.lower().endswith("export.xml")),
                            None,
                        )
                        if not xml_name:
                            raise HTTPException(
                                status_code=400,
                                detail="Could not find export.xml inside the ZIP. Make sure you are uploading the Apple Health export ZIP.",
                            )
                        # zf.open() returns a file-like object — iterparse reads it
                        # without extracting the full XML into memory
                        with zf.open(xml_name) as xml_file:
                            parser.parse_file(xml_file)
                except zipfile.BadZipFile:
                    raise HTTPException(status_code=400, detail="Invalid ZIP file.")
            else:
                parser.parse_file(tmp_path)

            synced = _persist_parsed(parser, current_user.id, db)

            integration.is_connected = True
            integration.last_synced_at = datetime.now(timezone.utc)
            log.status = "success"
            log.records_synced = synced
            log.completed_at = datetime.now(timezone.utc)
            db.commit()

            return {
                "status": "success",
                "records_imported": synced,
                "breakdown": {
                    "metrics": len(parser.metrics),
                    "sleep_sessions": len(parser.sleep_sessions),
                    "workouts": len(parser.workouts),
                    "nutrition_days": len(parser.nutrition_days),
                    "body_metric_days": len(parser.body_days),
                    "hydration_days": len(parser.hydration_days),
                },
            }
        except HTTPException:
            raise
        except Exception as e:
            log.status = "error"
            log.error_message = str(e)
            log.completed_at = datetime.now(timezone.utc)
            db.commit()
            raise HTTPException(status_code=500, detail=f"Parse error: {e}")
    finally:
        # Always clean up the temp file regardless of success or failure
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


@router.post("/webhook")
async def apple_health_webhook(
    request: Request,
    token: str = Query(..., description="Your user token — find it in Settings"),
    db: Session = Depends(get_db),
):
    """
    Real-time webhook for the 'Health Auto Export' iOS app.
    Configure the app with:  POST /api/integrations/apple-health/webhook?token=<YOUR_TOKEN>

    The app sends JSON payloads containing metric batches from HealthKit.
    """
    # Validate token (use the JWT sub claim as a simple bearer token)
    from app.api.auth import get_settings
    from jose import jwt, JWTError

    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
        user_id = int(payload.get("sub"))
    except (JWTError, TypeError, ValueError):
        raise HTTPException(status_code=401, detail="Invalid token")

    user = db.query(User).filter_by(id=user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    body = await request.json()
    integration = _get_or_create_integration(user, db)
    log = SyncLog(integration_id=integration.id)
    db.add(log)
    db.commit()

    try:
        synced = _process_health_auto_export(body, user.id, db)
        integration.last_synced_at = datetime.now(timezone.utc)
        integration.is_connected = True
        log.status = "success"
        log.records_synced = synced
        log.completed_at = datetime.now(timezone.utc)
        db.commit()
        return {"status": "ok", "records_synced": synced}
    except Exception as e:
        log.status = "error"
        log.error_message = str(e)
        log.completed_at = datetime.now(timezone.utc)
        db.commit()
        raise HTTPException(status_code=500, detail=str(e))


def _process_health_auto_export(body: dict, user_id: int, db: Session) -> int:
    """
    Process JSON payload from the 'Health Auto Export' iOS app.
    Format: { "data": { "metrics": [...], "workouts": [...] } }
    Each metric: { "name": "step_count", "units": "count", "data": [{"date":"...", "qty": N}] }
    """
    synced = 0
    data = body.get("data", body)  # some versions wrap, some don't

    # Metric name → our metric_type
    HAEX_MAP = {
        "step_count": "steps",
        "heart_rate": "heart_rate",
        "resting_heart_rate": "resting_heart_rate",
        "heart_rate_variability": "hrv",
        "oxygen_saturation": "spo2",
        "respiratory_rate": "respiratory_rate",
        "active_energy": "active_calories",
        "basal_body_temperature": "basal_calories",
        "walking_running_distance": "distance_walking_running",
        "flights_climbed": "flights_climbed",
        "vo2_max": "vo2_max",
        "mindful_minutes": "mindful_minutes",
        "exercise_time": "exercise_minutes",
        "weight_body_mass": "weight_kg",
        "body_fat_percentage": "body_fat_percent",
        "bmi": "bmi",
        "lean_body_mass": "fat_free_mass_kg",
        "dietary_energy": "calories",
        "protein": "protein_g",
        "carbohydrates": "carbs_g",
        "total_fat": "fat_g",
        "fiber": "fiber_g",
        "water": "hydration_ml",
    }

    for metric in data.get("metrics", []):
        name = metric.get("name", "").lower().replace(" ", "_")
        mapped = HAEX_MAP.get(name, name)
        units = metric.get("units", "")

        for entry in metric.get("data", []):
            qty = entry.get("qty") or entry.get("value")
            date_str = entry.get("date") or entry.get("startDate")
            if qty is None or not date_str:
                continue
            try:
                qty = float(qty)
                recorded_at = _parse_hk_date(date_str) or datetime.fromisoformat(date_str[:19]).replace(tzinfo=timezone.utc)
            except Exception:
                continue

            if mapped == "hydration_ml":
                if units.lower() in ("l", "liters"):
                    qty *= 1000
                h = HydrationRecord(
                    user_id=user_id, source=PLATFORM,
                    recorded_at=recorded_at, amount_ml=qty, daily_goal_ml=2000,
                )
                db.add(h)
            elif mapped in ("weight_kg", "bmi", "body_fat_percent", "fat_free_mass_kg"):
                if mapped == "weight_kg" and units.lower() in ("lb", "lbs"):
                    qty *= 0.453592
                elif mapped == "body_fat_percent" and qty <= 1.0:
                    qty *= 100
                bm = BodyMetric(
                    user_id=user_id, source=PLATFORM,
                    measured_at=recorded_at,
                    **{mapped: qty},
                )
                db.add(bm)
            elif mapped in ("calories", "protein_g", "carbs_g", "fat_g", "fiber_g"):
                day = recorded_at.strftime("%Y-%m-%d")
                nr = NutritionRecord(
                    user_id=user_id, source=PLATFORM,
                    recorded_date=recorded_at, meal_type="daily_total",
                    **{mapped: qty},
                )
                db.add(nr)
            else:
                m = HealthMetric(
                    user_id=user_id, source=PLATFORM,
                    metric_type=mapped, value=qty, unit=units,
                    recorded_at=recorded_at,
                )
                db.add(m)
            synced += 1

    # Workouts
    for w in data.get("workouts", []):
        start_dt = _parse_hk_date(w.get("start") or w.get("startDate", ""))
        end_dt = _parse_hk_date(w.get("end") or w.get("endDate", ""))
        if not start_dt:
            continue
        activity = ActivityRecord(
            user_id=user_id, source=PLATFORM,
            activity_type=w.get("name", "workout").lower().replace(" ", "_"),
            workout_name=w.get("name", "Workout"),
            start_time=start_dt,
            end_time=end_dt,
            duration_minutes=int(float(w["duration"])) if w.get("duration") else None,
            calories_burned=w.get("activeEnergy") or w.get("calories"),
            distance_km=w.get("distance"),
        )
        db.add(activity)
        synced += 1

    return synced


@router.post("/sync-native")
async def sync_native_apple_health(
    payload: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Called by the iOS mobile app after reading native HealthKit data.
    Accepts the same JSON shape as the webhook endpoint (Health Auto Export format).
    Uses standard JWT Bearer auth — no separate webhook token needed.
    """
    integration = _get_or_create_integration(current_user, db)
    log = SyncLog(integration_id=integration.id)
    db.add(log)
    db.commit()

    try:
        synced = _process_health_auto_export(payload, current_user.id, db)
        integration.is_connected = True
        integration.last_synced_at = datetime.now(timezone.utc)
        log.status = "success"
        log.records_synced = synced
        log.completed_at = datetime.now(timezone.utc)
        db.commit()
        return {"status": "ok", "records_synced": synced}
    except Exception as e:
        log.status = "error"
        log.error_message = str(e)
        log.completed_at = datetime.now(timezone.utc)
        db.commit()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/disconnect")
async def disconnect_apple_health(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    integration = db.query(Integration).filter_by(
        user_id=current_user.id, platform=PLATFORM
    ).first()
    if integration:
        integration.is_connected = False
        db.commit()
    return {"status": "disconnected"}


@router.get("/webhook-token")
async def get_webhook_token(
    current_user: User = Depends(get_current_user),
):
    """Return the user's JWT token to use as webhook auth token."""
    from datetime import timedelta
    from app.api.auth import create_access_token
    # Long-lived token for the webhook (1 year)
    token = create_access_token(
        {"sub": str(current_user.id)},
        expires_delta=timedelta(days=365),
    )
    return {"token": token, "user_id": current_user.id}
