"""
SetuAI — Projects Router

Minimal: only POST /projects exists (a project must exist before a schedule can
be uploaded to it). GET /projects/{id} etc. arrive when a later slice needs them.
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from config.database import get_db
from models.schemas import Project
from repositories import project_repository

router = APIRouter(prefix="/projects", tags=["projects"])


class CreateProjectRequest(BaseModel):
    name: str


@router.post("", response_model=Project)
def create_project(body: CreateProjectRequest, db: Session = Depends(get_db)) -> Project:
    if not body.name.strip():
        raise HTTPException(
            status_code=422,
            detail={"error": {"code": "VALIDATION_ERROR", "message": "Project name is required."}},
        )
    project = project_repository.create_project(db, body.name.strip())
    return Project(
        project_id=project.project_id, name=project.name, created_at=project.created_at
    )
