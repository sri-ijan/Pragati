"""SetuAI — Document repository. DB access for `source_documents` only."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from models.orm import SourceDocumentORM


def create_document(
    db: Session,
    source_document_id: str,
    project_id: str,
    filename: str,
    content_type: str,
    storage_path: str,
) -> SourceDocumentORM:
    doc = SourceDocumentORM(
        source_document_id=source_document_id,
        project_id=project_id,
        filename=filename,
        content_type=content_type,
        storage_path=storage_path,
        status="received",
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc


def get_documents_for_project(db: Session, project_id: str) -> list[SourceDocumentORM]:
    return list(
        db.execute(
            select(SourceDocumentORM)
            .where(SourceDocumentORM.project_id == project_id)
            .order_by(SourceDocumentORM.uploaded_at.desc())
        ).scalars()
    )
