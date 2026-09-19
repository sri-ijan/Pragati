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

from sqlalchemy import Date, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


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
