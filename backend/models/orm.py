"""
SetuAI — ORM Models (SQLAlchemy)

First real database tables (Slice 1). Deliberately kept separate from
models/schemas.py: schemas.py holds the Slice 0 locked API/domain contracts
(Pydantic) and is not touched here; this file holds the persistence layer.

Table creation for the MVP uses Base.metadata.create_all() at app startup
(see main.py) rather than Alembic migrations — logged in docs/DECISIONS.md as
a deliberate hackathon-scope simplification, revisit if schema churn gets
painful.
"""

import uuid
from datetime import date, datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import JSON, Date, DateTime, Float, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

# Kept as a literal (not imported from services.embeddings_provider) so this
# models/ file has no dependency on services/ — must match
# services/embeddings_provider.EMBEDDING_DIMENSIONS if that ever changes.
EMBEDDING_DIMENSIONS = 768


class Base(DeclarativeBase):
    pass


def _uuid() -> str:
    return str(uuid.uuid4())


class ProjectORM(Base):
    __tablename__ = "projects"

    project_id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    activities: Mapped[list["ScheduleActivityORM"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )


class ScheduleActivityORM(Base):
    __tablename__ = "schedule_activities"
    __table_args__ = (
        UniqueConstraint("project_id", "activity_id", name="uq_project_activity"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.project_id"))
    activity_id: Mapped[str] = mapped_column(String, nullable=False)
    wbs: Mapped[str] = mapped_column(String, nullable=False, default="")
    discipline: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(String, nullable=False)
    area: Mapped[str] = mapped_column(String, nullable=False, default="")
    planned_start: Mapped[date] = mapped_column(Date, nullable=False)
    planned_finish: Mapped[date] = mapped_column(Date, nullable=False)
    actual_start: Mapped[date | None] = mapped_column(Date, nullable=True)
    actual_finish: Mapped[date | None] = mapped_column(Date, nullable=True)

    project: Mapped["ProjectORM"] = relationship(back_populates="activities")


class SourceDocumentORM(Base):
    """
    A raw field upload (DPR/spreadsheet/text/image) — Slice 2. Extraction into
    ExecutionEvent rows (Slice 3) reads from here later; this table only
    records what was received and where it's stored on disk.
    """

    __tablename__ = "source_documents"

    source_document_id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.project_id"))
    filename: Mapped[str] = mapped_column(String, nullable=False)
    content_type: Mapped[str] = mapped_column(String, nullable=False)
    storage_path: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False, default="received")
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    project: Mapped["ProjectORM"] = relationship()


class ExecutionEventORM(Base):
    """
    A validated, LLM-extracted field event (Slice 3). One row per successful
    extraction call — extraction is not deduplicated per source document (a
    document can be re-extracted, producing another row); see
    docs/DECISIONS.md for why that's an accepted simplification for now.
    """

    __tablename__ = "execution_events"

    event_id: Mapped[str] = mapped_column(String, primary_key=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.project_id"))
    source_id: Mapped[str] = mapped_column(ForeignKey("source_documents.source_document_id"))
    discipline: Mapped[str] = mapped_column(String, nullable=False)
    activity_description: Mapped[str] = mapped_column(String, nullable=False)
    action: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False)
    location: Mapped[str] = mapped_column(String, nullable=False)
    equipment_tag: Mapped[str | None] = mapped_column(String, nullable=True)
    line_number: Mapped[str | None] = mapped_column(String, nullable=True)
    event_date: Mapped[date] = mapped_column(Date, nullable=False)
    quantity: Mapped[float | None] = mapped_column(Float, nullable=True)
    unit: Mapped[str | None] = mapped_column(String, nullable=True)
    raw_text: Mapped[str] = mapped_column(String, nullable=False)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    extracted_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ActivityEmbeddingORM(Base):
    """
    Cached embedding for a schedule activity (Slice 4). Computed lazily the
    first time a project's activities are needed for matching, then reused —
    not recomputed on every match request. One row per (project_id,
    activity_id); a schedule re-upload that changes a description will get a
    stale embedding until Slice 4's cache invalidation is revisited (see
    docs/DECISIONS.md — a known, flagged simplification).
    """

    __tablename__ = "activity_embeddings"
    __table_args__ = (
        UniqueConstraint("project_id", "activity_id", name="uq_project_activity_embedding"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.project_id"))
    activity_id: Mapped[str] = mapped_column(String, nullable=False)
    embedding: Mapped[list[float]] = mapped_column(Vector(EMBEDDING_DIMENSIONS), nullable=False)
    computed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ActivityMatchORM(Base):
    """
    One scored candidate from a matching run (Slice 4). A single
    POST /events/{id}/match call produces several rows (one per candidate);
    GET /events/{id}/candidates re-reads the latest batch for that event_id
    without recomputing. A fresh match run replaces the previous batch for
    the same event_id (see repositories/match_repository.py) rather than
    accumulating history — no audit trail for match runs themselves in this
    slice (that's schedule-update audit, Slice 5/6 territory, not this).
    """

    __tablename__ = "activity_matches"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    event_id: Mapped[str] = mapped_column(ForeignKey("execution_events.event_id"))
    candidate_activity_id: Mapped[str] = mapped_column(String, nullable=False)
    semantic_score: Mapped[float] = mapped_column(Float, nullable=False)
    metadata_score: Mapped[float] = mapped_column(Float, nullable=False)
    temporal_score: Mapped[float] = mapped_column(Float, nullable=False)
    llm_score: Mapped[float] = mapped_column(Float, nullable=False)
    terminology_score: Mapped[float] = mapped_column(Float, nullable=False)
    final_confidence: Mapped[float] = mapped_column(Float, nullable=False)
    decision: Mapped[str] = mapped_column(String, nullable=False)
    reviewer: Mapped[str | None] = mapped_column(String, nullable=True)
    reason: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    computed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)