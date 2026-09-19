"""
SetuAI — Schedule Router

POST /projects/{id}/schedule/upload and GET /projects/{id}/schedule. Excel/CSV
parsing lives in services/schedule_parser.py; DB access lives in
repositories/schedule_repository.py — this module only wires them together and
shapes the HTTP response per docs/API.md.
"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlalchemy.orm import Session

from config.database import get_db
from config.settings import settings
from models.schemas import ScheduleActivity, UploadScheduleResponse
from repositories import project_repository, schedule_repository
from services.schedule_parser import parse_schedule_file

router = APIRouter(prefix="/projects", tags=["schedule"])


def _get_project_or_404(db: Session, project_id: str):
    project = project_repository.get_project(db, project_id)
    if project is None:
        raise HTTPException(
            status_code=404,
            detail={
                "error": {
                    "code": "NOT_FOUND",
                    "message": f"Project '{project_id}' does not exist.",
                }
            },
        )
    return project


@router.post("/{project_id}/schedule/upload", response_model=UploadScheduleResponse)
async def upload_schedule(
    project_id: str, file: UploadFile, db: Session = Depends(get_db)
) -> UploadScheduleResponse:
    _get_project_or_404(db, project_id)

    content = await file.read()
    if len(content) > settings.max_upload_bytes:
        raise HTTPException(
            status_code=413,
            detail={
                "error": {
                    "code": "FILE_TOO_LARGE",
                    "message": "Schedule file exceeds the 10 MB limit.",
                }
            },
        )

    activities, warnings = parse_schedule_file(file.filename or "upload", content)

    if not activities:
        raise HTTPException(
            status_code=422,
            detail={
                "error": {
                    "code": "SCHEDULE_PARSE_ERROR",
                    "message": "No valid schedule activities found in the file.",
                    "details": {"warnings": warnings},
                }
            },
        )

    inserted = schedule_repository.bulk_insert_activities(db, project_id, activities)
    skipped_as_duplicates = len(activities) - inserted
    if skipped_as_duplicates:
        warnings.append(
            f"{skipped_as_duplicates} activity ID(s) already existed for this project and were skipped."
        )

    return UploadScheduleResponse(
        project_id=project_id, activities_imported=inserted, warnings=warnings
    )


@router.get("/{project_id}/schedule", response_model=list[ScheduleActivity])
def get_schedule(project_id: str, db: Session = Depends(get_db)) -> list[ScheduleActivity]:
    _get_project_or_404(db, project_id)
    rows = schedule_repository.get_activities_for_project(db, project_id)
    return [
        ScheduleActivity(
            activity_id=row.activity_id,
            wbs=row.wbs,
            discipline=row.discipline,
            description=row.description,
            area=row.area,
            planned_start=row.planned_start,
            planned_finish=row.planned_finish,
            actual_start=row.actual_start,
            actual_finish=row.actual_finish,
        )
        for row in rows
    ]
