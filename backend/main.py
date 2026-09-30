"""
SetuAI — Backend Entrypoint

Run from inside backend/:
    uvicorn main:app --reload --port 8000

Slice 0 scaffolding + Slice 1 (schedule ingestion). Feature routers are added
slice by slice: projects + schedule now; documents/extraction/matching/review/
analytics/audit-log/memory-query (docs/API.md) arrive with their own slices.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from api.documents import router as documents_router
from api.extraction import router as extraction_router
from api.health import router as health_router
from api.matching import router as matching_router
from api.projects import router as projects_router
from api.schedule import router as schedule_router
from config.database import engine
from config.settings import settings
from models.orm import Base


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Creates the pgvector extension (Slice 4 — activity_embeddings) and any
    # tables that don't exist yet. MVP uses create_all instead of migrations —
    # see docs/DECISIONS.md. Never blocks/crashes startup if Postgres isn't
    # reachable yet — matches the lazy-connection scaffolding decision from
    # the earlier scaffolding pass.
    try:
        from sqlalchemy import text

        with engine.connect() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            conn.commit()
        Base.metadata.create_all(bind=engine)
    except Exception as exc:  # noqa: BLE001
        print(f"[startup] Could not create extension/tables (DB unreachable?): {exc}")
    yield


app = FastAPI(
    title="SetuAI API",
    description="Planning-to-Execution Bridge — AI Field-to-Schedule Reconciliation (SIH PS 122)",
    version="0.1.0",
    lifespan=lifespan,
)

# Dev-only CORS: allow the local Next.js frontend to call this API.
# No auth is implemented for the MVP (docs/API.md, docs/DECISIONS.md).
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """
    Normalizes every error response to the docs/API.md envelope:
        { "error": { "code", "message", "details" } }
    Routes raise HTTPException with detail already in that shape (see api/schedule.py,
    api/projects.py); anything that doesn't is wrapped here so the shape is never broken.
    """
    if isinstance(exc.detail, dict) and "error" in exc.detail:
        return JSONResponse(status_code=exc.status_code, content=exc.detail)
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": "HTTP_ERROR", "message": str(exc.detail)}},
    )


app.include_router(health_router)
app.include_router(projects_router)
app.include_router(schedule_router)
app.include_router(documents_router)
app.include_router(extraction_router)
app.include_router(matching_router)