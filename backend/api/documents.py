"""
SetuAI — Documents Router (Slice 2)

POST /projects/{id}/documents/upload — contracted in docs/API.md.
GET  /projects/{id}/documents — NOT in the original contract list. Added here
so uploaded documents are actually visible to something other than the DB
directly (mirrors GET /projects/{id}/schedule, which was already contracted).
Logged as a contract extension in docs/DECISIONS.md and reflected in
docs/API.md — not a silent change to any existing shape.

Extraction into ExecutionEvent rows is Slice 3 — this module only stores the
raw upload and a DB record of it.
"""

from datetime import datetime
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session

from config.database import get_db
from config.settings import settings
from models.schemas import UploadDocumentResponse
from repositories import document_repository, project_repository
from services.document_storage import save_uploaded_document

router = APIRouter(prefix="/projects", tags=["documents"])

# Per docs/API.md "Upload Constraints" for document uploads.
ALLOWED_EXTENSIONS = {".pdf", ".txt", ".docx", ".xlsx", ".csv", ".jpg", ".jpeg", ".png"}
# Extensions that Slice 3 extraction won't be able to read yet even once built
# (OCR is P2/optional per plan.md) — accepted at the API level per the contract,
# but flagged back to the caller so the UI can set expectations.
UNPROCESSABLE_YET = {".jpg", ".jpeg", ".png"}


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


@router.post("/{project_id}/documents/upload", response_model=UploadDocumentResponse)
async def upload_document(
    project_id: str, file: UploadFile, db: Session = Depends(get_db)
) -> UploadDocumentResponse:
    _get_project_or_404(db, project_id)

    filename = file.filename or "upload"
    ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=422,
            detail={
                "error": {
                    "code": "UNSUPPORTED_FILE_TYPE",
                    "message": f"'{ext or filename}' is not an accepted document type.",
                    "details": {"accepted": sorted(ALLOWED_EXTENSIONS)},
                }
            },
        )

    content = await file.read()
    if len(content) > settings.max_upload_bytes:
        raise HTTPException(
            status_code=413,
            detail={
                "error": {
                    "code": "FILE_TOO_LARGE",
                    "message": "Document exceeds the 10 MB limit.",
                }
            },
        )

    # Generated up front so the same ID names both the DB row and the storage folder.
    source_document_id = str(uuid4())
    storage_path = save_uploaded_document(project_id, source_document_id, filename, content)

    document_repository.create_document(
        db,
        source_document_id=source_document_id,
        project_id=project_id,
        filename=filename,
        content_type=file.content_type or "application/octet-stream",
        storage_path=storage_path,
    )

    return UploadDocumentResponse(
        source_document_id=source_document_id,
        filename=filename,
        status="received",
    )


class DocumentSummary(BaseModel):
    source_document_id: str
    filename: str
    content_type: str
    status: str
    uploaded_at: datetime
    processable_now: bool  # false for image types until OCR (P2) exists


@router.get("/{project_id}/documents", response_model=list[DocumentSummary])
def list_documents(project_id: str, db: Session = Depends(get_db)) -> list[DocumentSummary]:
    _get_project_or_404(db, project_id)
    rows = document_repository.get_documents_for_project(db, project_id)
    return [
        DocumentSummary(
            source_document_id=row.source_document_id,
            filename=row.filename,
            content_type=row.content_type,
            status=row.status,
            uploaded_at=row.uploaded_at,
            processable_now=not any(row.filename.lower().endswith(e) for e in UNPROCESSABLE_YET),
        )
        for row in rows
    ]
