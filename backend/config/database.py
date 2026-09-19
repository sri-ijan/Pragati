"""
SetuAI — Database Connection Scaffolding

Slice 0/1 scaffolding only. Provides a SQLAlchemy engine + session dependency so
later slices can start defining real tables (schedule_activities, execution_events,
etc. — see docs/API.md "Database Tables") without re-wiring the connection.

Deliberately does NOT:
- define any ORM models / tables (that's a later slice, per plan.md §23 table list)
- run migrations
- require Postgres to be up for the backend process to start (engine creation is
  lazy; connections are only opened when a request actually needs one)
"""

from collections.abc import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from config.settings import settings

# pool_pre_ping avoids handing out dead connections after Postgres restarts.
engine = create_engine(settings.database_url, pool_pre_ping=True)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency — yields a DB session, closes it after the request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def check_db_connection() -> tuple[bool, str | None]:
    """Used by the optional /health/db endpoint. Never raises — returns (ok, error)."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True, None
    except Exception as exc:  # noqa: BLE001 — health check must never crash the app
        return False, str(exc)
