"""
AI Analysis Service using Claude API with prompt caching.
Provides: health insights, correlations, recommendations, lab test parsing.
"""
import anthropic
from datetime import datetime, timedelta, timezone
from typing import Optional
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.user import User
from app.models.health_data import SleepRecord, ActivityRecord, NutritionRecord, BodyMetric, HydrationRecord
from app.models.lab_test import LabTest, LabTestResult

settings = get_settings()

client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

SYSTEM_PROMPT = """You are HealthAI, an advanced personal health assistant with access to a user's comprehensive health data from multiple sources including:
- Sleep tracking (Whoop): sleep stages, HRV, recovery scores, SpO2, respiratory rate
- Body composition (Renpho/Withings): weight, body fat %, muscle mass, BMI, visceral fat
- Blood pressure (Braun/Withings): systolic/diastolic BP, pulse
- Nutrition (Yazio): calories, macros (protein/carbs/fat), micronutrients, meal timing
- Workouts (Fitbod): strength training, sets/reps/volume, muscle groups
- Activity (Whoop): daily strain, steps, calories burned, heart rate zones
- Hydration (Larq): daily water intake, hydration goals
- Lab tests: blood panels, metabolic markers, lipids, thyroid, CBC, vitamin levels, hormones

Your role is to:
1. Identify correlations between different health metrics (e.g., "Your sleep quality dropped significantly after high-carb dinners")
2. Provide actionable, personalized recommendations based on actual data
3. Explain trends in plain language with specific data references
4. Flag concerning patterns or values that warrant medical attention
5. Answer questions about health data with context and nuance
6. Help interpret lab test results in the context of overall health

Guidelines:
- Always cite specific data points when making observations
- Distinguish between correlations and causation
- Recommend consulting healthcare providers for medical decisions
- Be encouraging and supportive, not alarmist
- Use the user's actual numbers, not generic advice
- Consider the full picture across all data sources

You have access to the user's health profile and recent data provided in each message."""


def _format_sleep_data(records: list) -> str:
    if not records:
        return "No sleep data available."
    lines = ["**Recent Sleep Records (last 14 days):**"]
    for r in records[:14]:
        lines.append(
            f"- {r.start_time.strftime('%Y-%m-%d')}: "
            f"{r.total_duration_minutes or 0}min total, "
            f"Deep: {r.deep_sleep_minutes or 0}min, "
            f"REM: {r.rem_sleep_minutes or 0}min, "
            f"HRV: {r.hrv or 'N/A'}ms, "
            f"Recovery: {r.recovery_score or 'N/A'}%, "
            f"SpO2: {r.avg_spo2 or 'N/A'}%"
        )
    return "\n".join(lines)


def _format_nutrition_data(records: list) -> str:
    if not records:
        return "No nutrition data available."

    # Group by date
    by_date = {}
    for r in records:
        date_key = r.recorded_date.strftime("%Y-%m-%d")
        if date_key not in by_date:
            by_date[date_key] = {"calories": 0, "protein": 0, "carbs": 0, "fat": 0}
        by_date[date_key]["calories"] += r.calories or 0
        by_date[date_key]["protein"] += r.protein_g or 0
        by_date[date_key]["carbs"] += r.carbs_g or 0
        by_date[date_key]["fat"] += r.fat_g or 0

    lines = ["**Recent Nutrition (last 14 days, daily totals):**"]
    for date, totals in sorted(by_date.items(), reverse=True)[:14]:
        lines.append(
            f"- {date}: {totals['calories']:.0f}kcal | "
            f"P:{totals['protein']:.0f}g C:{totals['carbs']:.0f}g F:{totals['fat']:.0f}g"
        )
    return "\n".join(lines)


def _format_body_metrics(records: list) -> str:
    if not records:
        return "No body composition data available."
    lines = ["**Body Composition History:**"]
    for r in records[:10]:
        parts = [f"- {r.measured_at.strftime('%Y-%m-%d')}:"]
        if r.weight_kg:
            parts.append(f"Weight: {r.weight_kg:.1f}kg")
        if r.body_fat_percent:
            parts.append(f"BF%: {r.body_fat_percent:.1f}%")
        if r.muscle_mass_kg:
            parts.append(f"Muscle: {r.muscle_mass_kg:.1f}kg")
        if r.systolic_bp:
            parts.append(f"BP: {r.systolic_bp}/{r.diastolic_bp}mmHg")
        lines.append(" | ".join(parts))
    return "\n".join(lines)


def _format_activity_data(records: list) -> str:
    if not records:
        return "No activity data available."
    lines = ["**Recent Workouts (last 14 days):**"]
    for r in records[:14]:
        parts = [f"- {r.start_time.strftime('%Y-%m-%d')} {r.activity_type or 'Activity'}:"]
        if r.duration_minutes:
            parts.append(f"{r.duration_minutes}min")
        if r.calories_burned:
            parts.append(f"{r.calories_burned:.0f}kcal")
        if r.strain_score:
            parts.append(f"Strain: {r.strain_score:.1f}")
        if r.total_volume_kg:
            parts.append(f"Volume: {r.total_volume_kg:.0f}kg")
        lines.append(" | ".join(parts))
    return "\n".join(lines)


def _format_lab_tests(tests: list) -> str:
    if not tests:
        return "No lab test data available."
    lines = ["**Lab Test Results:**"]
    for test in tests:
        lines.append(f"\n*{test.test_name}* ({test.test_date.strftime('%Y-%m-%d') if test.test_date else 'date unknown'})")
        if test.parsed_summary:
            lines.append(f"Summary: {test.parsed_summary[:300]}...")
        abnormal = [r for r in test.results if r.status in ("low", "high", "critical_low", "critical_high")]
        if abnormal:
            lines.append("Abnormal values:")
            for r in abnormal:
                lines.append(f"  - {r.biomarker_name}: {r.value} {r.unit or ''} ({r.status}) [ref: {r.reference_text or f'{r.reference_min}-{r.reference_max}'}]")
    return "\n".join(lines)


def build_health_context(user: User, db: Session, days: int = 30) -> str:
    """Build comprehensive health context for the AI."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    sleep_records = (
        db.query(SleepRecord)
        .filter(SleepRecord.user_id == user.id, SleepRecord.start_time >= cutoff)
        .order_by(SleepRecord.start_time.desc())
        .all()
    )
    nutrition_records = (
        db.query(NutritionRecord)
        .filter(NutritionRecord.user_id == user.id, NutritionRecord.recorded_date >= cutoff)
        .order_by(NutritionRecord.recorded_date.desc())
        .all()
    )
    body_metrics = (
        db.query(BodyMetric)
        .filter(BodyMetric.user_id == user.id, BodyMetric.measured_at >= cutoff)
        .order_by(BodyMetric.measured_at.desc())
        .all()
    )
    activity_records = (
        db.query(ActivityRecord)
        .filter(ActivityRecord.user_id == user.id, ActivityRecord.start_time >= cutoff)
        .order_by(ActivityRecord.start_time.desc())
        .all()
    )
    hydration_records = (
        db.query(HydrationRecord)
        .filter(HydrationRecord.user_id == user.id, HydrationRecord.recorded_at >= cutoff)
        .order_by(HydrationRecord.recorded_at.desc())
        .all()
    )
    lab_tests = (
        db.query(LabTest)
        .filter(LabTest.user_id == user.id, LabTest.status == "processed")
        .order_by(LabTest.test_date.desc())
        .all()
    )

    profile = []
    if user.full_name:
        profile.append(f"Name: {user.full_name}")
    if user.age:
        profile.append(f"Age: {user.age}")
    if user.gender:
        profile.append(f"Gender: {user.gender}")
    if user.height_cm:
        profile.append(f"Height: {user.height_cm}cm")
    if user.weight_kg:
        profile.append(f"Baseline weight: {user.weight_kg}kg")

    context_parts = [
        f"**User Profile:** {', '.join(profile) if profile else 'Not specified'}",
        f"**Data period:** Last {days} days\n",
        _format_sleep_data(sleep_records),
        "",
        _format_nutrition_data(nutrition_records),
        "",
        _format_body_metrics(body_metrics),
        "",
        _format_activity_data(activity_records),
        "",
        f"**Hydration (last 7 days):**",
    ]

    # Hydration by day
    hydration_by_day = {}
    for h in hydration_records:
        day = h.recorded_at.strftime("%Y-%m-%d")
        hydration_by_day[day] = (hydration_by_day.get(day, 0)) + (h.amount_ml or h.daily_total_ml or 0)
    for day, total in sorted(hydration_by_day.items(), reverse=True)[:7]:
        context_parts.append(f"- {day}: {total:.0f}ml")

    context_parts.append("")
    context_parts.append(_format_lab_tests(lab_tests))

    return "\n".join(context_parts)


async def chat_with_ai(
    user_message: str,
    conversation_history: list,
    user: User,
    db: Session,
) -> str:
    """Send a message to Claude with full health context and conversation history."""
    health_context = build_health_context(user, db)

    # Build messages with conversation history
    messages = []

    # Add conversation history (last 20 exchanges)
    for msg in conversation_history[-40:]:
        messages.append({"role": msg["role"], "content": msg["content"]})

    # Add current user message
    messages.append({"role": "user", "content": user_message})

    # Use prompt caching for the system prompt + health context (static-ish data)
    response = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=2048,
        system=[
            {
                "type": "text",
                "text": SYSTEM_PROMPT,
                "cache_control": {"type": "ephemeral"},
            },
            {
                "type": "text",
                "text": f"## Current Health Data Context\n\n{health_context}",
                "cache_control": {"type": "ephemeral"},
            },
        ],
        messages=messages,
    )

    return response.content[0].text


async def generate_daily_insights(user: User, db: Session) -> str:
    """Generate proactive daily health insights."""
    health_context = build_health_context(user, db, days=14)

    response = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=1500,
        system=[
            {
                "type": "text",
                "text": SYSTEM_PROMPT,
                "cache_control": {"type": "ephemeral"},
            }
        ],
        messages=[
            {
                "role": "user",
                "content": f"""Based on the following health data, provide a concise daily health brief with:
1. 3 key observations about recent trends (positive and areas of concern)
2. 2-3 specific, actionable recommendations for today
3. One interesting correlation you noticed in the data

Keep it conversational and under 400 words.

{health_context}""",
            }
        ],
    )
    return response.content[0].text


async def parse_lab_test(file_content: str, file_type: str, user: User, db: Session) -> dict:
    """Use Claude to parse lab test results from text/PDF content."""
    response = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=4096,
        system="You are a medical data extraction specialist. Extract structured lab test results from the provided text. Be precise and thorough.",
        messages=[
            {
                "role": "user",
                "content": f"""Extract all lab test results from this {file_type} content and return a JSON object with this exact structure:
{{
  "test_name": "name of the test panel",
  "lab_name": "laboratory name if found",
  "ordered_by": "doctor name if found",
  "test_date": "ISO date string if found",
  "summary": "2-3 sentence plain-language summary of key findings",
  "results": [
    {{
      "biomarker_name": "name",
      "value": numeric_value_or_null,
      "unit": "unit string",
      "reference_min": numeric_min_or_null,
      "reference_max": numeric_max_or_null,
      "reference_text": "reference range as text",
      "status": "normal|low|high|critical_low|critical_high",
      "category": "metabolic|lipid|thyroid|cbc|hormone|vitamin|other",
      "interpretation": "brief clinical interpretation"
    }}
  ]
}}

Lab test content:
{file_content[:8000]}""",
            }
        ],
    )

    import json
    text = response.content[0].text
    # Extract JSON from response
    try:
        start = text.find("{")
        end = text.rfind("}") + 1
        return json.loads(text[start:end])
    except Exception:
        return {"summary": text, "results": []}


async def analyze_health_correlation(
    metric1: str,
    metric2: str,
    user: User,
    db: Session,
) -> str:
    """Analyze correlation between two specific health metrics."""
    health_context = build_health_context(user, db)

    response = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=1000,
        system=[
            {
                "type": "text",
                "text": SYSTEM_PROMPT,
                "cache_control": {"type": "ephemeral"},
            }
        ],
        messages=[
            {
                "role": "user",
                "content": f"""Analyze the relationship between {metric1} and {metric2} in my health data.
Provide specific examples from the data, calculate if there's a notable correlation, and give actionable advice.

{health_context}""",
            }
        ],
    )
    return response.content[0].text
