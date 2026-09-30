"""SetuAI — Execution event repository. DB access for `execution_events` only."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from models.orm import ExecutionEventORM
from models.schemas import ExecutionEvent


def save_execution_event(db: Session, project_id: str, event: ExecutionEvent) -> ExecutionEventORM:
    row = ExecutionEventORM(
        event_id=event.event_id,
        project_id=project_id,
        source_id=event.source_id,
        discipline=event.discipline.value,
        activity_description=event.activity_description,
        action=event.action,
        status=event.status.value,
        location=event.location,
        equipment_tag=event.equipment_tag,
        line_number=event.line_number,
        event_date=event.event_date,
        quantity=event.quantity,
        unit=event.unit,
        raw_text=event.raw_text,
        confidence=event.confidence,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def get_event_by_id(db: Session, event_id: str) -> ExecutionEventORM | None:
    return db.get(ExecutionEventORM, event_id)


def get_events_for_project(
    db: Session, project_id: str, status: str | None = None
) -> list[ExecutionEventORM]:
    stmt = select(ExecutionEventORM).where(ExecutionEventORM.project_id == project_id)
    if status:
        stmt = stmt.where(ExecutionEventORM.status == status)
    stmt = stmt.order_by(ExecutionEventORM.extracted_at.desc())
    return list(db.execute(stmt).scalars())