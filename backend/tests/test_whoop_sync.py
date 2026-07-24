"""
Tests for the Whoop sync — verifies that a successful sync populates the
records the dashboard actually renders (sleep + activity), and that partial
failures (e.g. a missing OAuth scope) are surfaced instead of swallowed.

Run:  cd backend && pytest -q
"""
import os
from datetime import datetime, timezone, timedelta

os.environ.setdefault("DATABASE_URL", "sqlite:////tmp/whoop_test_app.db")

import httpx
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models.user import User
from app.models.integration import Integration
from app.models.health_data import SleepRecord, ActivityRecord, HealthMetric, BodyMetric
from app.api.integrations import whoop as whoop_module

NOW = datetime.now(timezone.utc)


# ── Fake Whoop HTTP layer ─────────────────────────────────────────────────────

def _iso(dt: datetime) -> str:
    return dt.isoformat().replace("+00:00", "Z")


def _recovery(sleep_id: int) -> dict:
    return {
        "cycle_id": 900 + sleep_id,
        "sleep_id": sleep_id,
        "score_state": "SCORED",
        "score": {
            "recovery_score": 66,
            "resting_heart_rate": 52,
            "hrv_rmssd_milli": 45.3,
            "spo2_percentage": 96.5,
            "skin_temp_celsius": 33.1,
        },
    }


def _sleep(sleep_id: int, day: int) -> dict:
    start = NOW - timedelta(days=day, hours=8)
    end = NOW - timedelta(days=day)
    return {
        "id": sleep_id,
        "start": _iso(start),
        "end": _iso(end),
        "nap": False,
        "score_state": "SCORED",
        "score": {
            "stage_summary": {
                "total_in_bed_time_milli": 8 * 3600 * 1000,
                "total_awake_time_milli": 30 * 60 * 1000,
                "total_light_sleep_time_milli": 4 * 3600 * 1000,
                "total_slow_wave_sleep_time_milli": 2 * 3600 * 1000,   # 120 min deep
                "total_rem_sleep_time_milli": 90 * 60 * 1000,          # 90 min REM
            },
            "sleep_efficiency_percentage": 92.0,
            "sleep_performance_percentage": 88.0,
            "respiratory_rate": 14.2,
        },
    }


def _workout(wid: int, day: int) -> dict:
    start = NOW - timedelta(days=day, hours=2)
    end = NOW - timedelta(days=day, hours=1)
    return {
        "id": wid,
        "start": _iso(start),
        "end": _iso(end),
        "sport_id": 0,  # Running
        "score_state": "SCORED",
        "score": {
            "strain": 12.5,
            "average_heart_rate": 140,
            "max_heart_rate": 175,
            "kilojoule": 2000.0,
            "distance_meter": 8000.0,
        },
    }


def _cycle(cid: int, day: int) -> dict:
    return {
        "id": cid,
        "start": _iso(NOW - timedelta(days=day)),
        "score_state": "SCORED",
        "score": {"strain": 14.0, "average_heart_rate": 70, "max_heart_rate": 180, "kilojoule": 9000.0},
    }


BODY = {"height_meter": 1.80, "weight_kilogram": 75.0, "max_heart_rate": 195}


class FakeResponse:
    def __init__(self, status: int, payload):
        self.status_code = status
        self._payload = payload
        self.text = str(payload)

    def json(self):
        return self._payload


class FakeClient:
    """Async context-manager stand-in for httpx.AsyncClient."""

    def __init__(self, routes):
        self.routes = routes

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def get(self, url, headers=None, params=None):
        for suffix, resp in self.routes.items():
            if url.endswith(suffix):
                return resp
        return FakeResponse(404, {"error": "not found"})


def _collection(records):
    return FakeResponse(200, {"records": records, "next_token": None})


def _make_db():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()

    user = User(email="a@b.c", hashed_password="x")
    db.add(user)
    db.commit()

    integration = Integration(
        user_id=user.id, platform="whoop", is_connected=True,
        access_token="tok", refresh_token="ref",
        token_scope="offline read:sleep read:recovery read:cycles read:workout read:body_measurement read:profile",
        token_expires_at=NOW + timedelta(days=1),
    )
    db.add(integration)
    db.commit()
    return db, user


def _patch_client(monkeypatch, routes):
    monkeypatch.setattr(whoop_module.httpx, "AsyncClient", lambda *a, **k: FakeClient(routes))


# ── Tests ─────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_sync_populates_dashboard_records(monkeypatch):
    db, user = _make_db()
    routes = {
        "/recovery": _collection([_recovery(1), _recovery(2)]),
        "/activity/sleep": _collection([_sleep(1, 1), _sleep(2, 2)]),
        "/activity/workout": _collection([_workout(10, 1)]),
        "/cycle": _collection([_cycle(100, 1), _cycle(101, 2)]),
        "/user/measurement/body": FakeResponse(200, BODY),
        "/user/profile/basic": FakeResponse(200, {"user_id": 5, "email": "a@b.c"}),
    }
    _patch_client(monkeypatch, routes)

    result = await whoop_module.sync_whoop(user, db, days=30)

    assert result["errors"] == {}
    assert result["status"] == "success"

    # Sleep — the records the dashboard's HRV/recovery/sleep charts read.
    sleeps = db.query(SleepRecord).order_by(SleepRecord.external_id).all()
    assert len(sleeps) == 2
    s = sleeps[0]
    assert s.hrv == 45.3                 # merged from /recovery
    assert s.recovery_score == 66        # merged from /recovery
    assert s.avg_spo2 == 96.5
    assert s.min_heart_rate == 52        # resting HR
    assert s.deep_sleep_minutes == 120   # stage nesting fixed (score.stage_summary)
    assert s.rem_sleep_minutes == 90
    assert s.respiratory_rate == 14.2

    # Activity — dashboard strain/calories.
    acts = db.query(ActivityRecord).all()
    assert len(acts) == 1
    a = acts[0]
    assert a.activity_type == "Running"
    assert a.strain_score == 12.5
    assert a.distance_km == 8.0
    assert round(a.calories_burned) == round(2000.0 * whoop_module.KJ_TO_KCAL)
    assert a.duration_minutes == 60

    # Cycle -> HealthMetric rows (don't pollute activity).
    strains = db.query(HealthMetric).filter_by(metric_type="day_strain").all()
    assert len(strains) == 2
    assert strains[0].value == 14.0

    # Body upsert -> single row.
    assert db.query(BodyMetric).filter_by(source="whoop").count() == 1


@pytest.mark.asyncio
async def test_missing_scope_endpoints_are_reported(monkeypatch):
    """Sleep/workout return 403 (scope not granted) -> surfaced, not swallowed."""
    db, user = _make_db()
    routes = {
        "/recovery": _collection([]),
        "/activity/sleep": FakeResponse(403, {"errors": [{"code": "insufficient_scope"}]}),
        "/activity/workout": FakeResponse(403, {"errors": [{"code": "insufficient_scope"}]}),
        "/cycle": _collection([_cycle(100, 1)]),
        "/user/measurement/body": FakeResponse(200, BODY),
    }
    _patch_client(monkeypatch, routes)

    result = await whoop_module.sync_whoop(user, db, days=30)

    assert result["status"] == "partial"
    assert set(result["errors"]) == {"sleep", "workout"}
    assert result["errors"]["sleep"]["status"] == 403
    # cycle + body still succeeded
    assert db.query(HealthMetric).filter_by(metric_type="day_strain").count() == 1
    assert db.query(SleepRecord).count() == 0
    assert db.query(ActivityRecord).count() == 0
