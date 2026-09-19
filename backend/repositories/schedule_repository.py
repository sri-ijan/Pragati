"""SetuAI — Schedule activity repository. DB access for `schedule_activities` only."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from models.orm import ScheduleActivityORM
from models.schemas import ScheduleActivity


def bulk_insert_activities(
    db: Session, project_id: str, activities: list[ScheduleActivity]
) -> int:
    """Inserts parsed activities for a project. Skips any activity_id already stored
    for this project (idempotent-ish re-upload) rather than erroring the whole batch."""
    existing_ids = set(
        db.execute(
            select(ScheduleActivityORM.activity_id).where(
                ScheduleActivityORM.project_id == project_id
            )
        ).scalars()
    )

    inserted = 0
    for activity in activities:
        if activity.activity_id in existing_ids:
            continue
        db.add(
            ScheduleActivityORM(
                project_id=project_id,
                activity_id=activity.activity_id,
                wbs=activity.wbs,
                discipline=activity.discipline.value,
                description=activity.description,
                area=activity.area,
                planned_start=activity.planned_start,
                planned_finish=activity.planned_finish,
                actual_start=activity.actual_start,
                actual_finish=activity.actual_finish,
            )
        )
        inserted += 1

    db.commit()
    return inserted


def get_activities_for_project(db: Session, project_id: str) -> list[ScheduleActivityORM]:
    return list(
        db.execute(
            select(ScheduleActivityORM).where(ScheduleActivityORM.project_id == project_id)
        ).scalars()
    )
