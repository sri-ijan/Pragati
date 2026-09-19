"""
SetuAI — Document Storage (Slice 2)

Writes uploaded field-report files to local disk under:
    data/uploads/{project_id}/{source_document_id}/{filename}

This matches the MVP storage decision in docs/API.md / docs/DECISIONS.md
(local disk for the hackathon; object storage would replace this function's
body in production without touching callers).
"""

from pathlib import Path

from config.settings import settings


def save_uploaded_document(
    project_id: str, source_document_id: str, filename: str, content: bytes
) -> str:
    """Writes the file to disk and returns the storage path (as a string)."""
    target_dir = settings.uploads_dir / project_id / source_document_id
    target_dir.mkdir(parents=True, exist_ok=True)

    # Filenames come from the client — strip any path components so a crafted
    # filename can't write outside target_dir.
    safe_filename = Path(filename).name or "upload"
    target_path = target_dir / safe_filename

    target_path.write_bytes(content)
    return str(target_path)
