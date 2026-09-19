"""
SetuAI — Health Router

Scaffolding-verification endpoints only. No feature routes live here — those
arrive with their own slice (schedule upload, extraction, matching, ...) and get
their own router module under api/.
"""

from fastapi import APIRouter

from config.database import check_db_connection

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict:
    """Liveness check — confirms the FastAPI app is running. Does not touch the DB."""
    return {"status": "ok", "service": "setuai-backend"}


@router.get("/health/db")
def health_db() -> dict:
    """
    Readiness check for the Postgres connection scaffolding.
    Returns 200 with connected=false (not a 5xx) when the DB is unreachable —
    this endpoint's job is to report status, not to gate the backend's own startup.
    """
    ok, error = check_db_connection()
    return {"connected": ok, "error": error}
