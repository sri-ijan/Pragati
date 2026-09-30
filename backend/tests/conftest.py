"""
SetuAI — Test Configuration

Inserts backend/ (this file's parent) onto sys.path so tests can import
`services.X`, `models.X` etc. the same absolute way the app code does,
regardless of the directory pytest is invoked from. Avoids depending on
whichever fix (or non-fix) `uvicorn backend.main:app` vs `uvicorn main:app`
ends up needing — that's a separate, unrelated concern.
"""

import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from models.orm import Base


@pytest.fixture()
def db_session():
    """A throwaway in-memory SQLite session with all tables created — used to
    test real persistence (execution_events) without requiring Postgres."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    session = Session(bind=engine)
    try:
        yield session
    finally:
        session.close()
        engine.dispose()