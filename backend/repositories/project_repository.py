"""SetuAI — Project repository. DB access for the `projects` table only."""

from sqlalchemy.orm import Session

from models.orm import ProjectORM


def create_project(db: Session, name: str) -> ProjectORM:
    project = ProjectORM(name=name)
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


def get_project(db: Session, project_id: str) -> ProjectORM | None:
    return db.get(ProjectORM, project_id)
