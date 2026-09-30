"""
SetuAI — Document Text Extraction (Slice 3)

Turns a stored source document's raw bytes into plain text for LLM
extraction. Deliberately minimal, matching "text/content extraction if
needed" rather than a general document-parsing subsystem:

- .txt is read directly — this is what typed field updates become
  (frontend/components/FieldUpdateForm.tsx wraps them client-side).
- .pdf gets basic text-LAYER extraction only (pypdf) — no OCR. A
  scanned/image-only PDF will yield no text and is reported as unsupported,
  not silently passed through as empty input.
- Everything else (.docx, .xlsx, .csv, .jpg, .png) raises
  UnsupportedForExtraction rather than guessing at how to read it. Building
  real parsers for those is out of scope for "the first AI layer" — this
  keeps failures honest instead of half-working.
"""

from __future__ import annotations

import io


class UnsupportedForExtraction(RuntimeError):
    """Raised when a stored document's type/content can't be turned into text yet."""


# Single source of truth for "can extraction actually run on this file" — used
# by api/documents.py to keep its processable_now flag honest rather than
# drifting from what this module actually supports.
EXTRACTABLE_EXTENSIONS = {".txt", ".pdf"}


def extract_text(filename: str, content: bytes) -> str:
    ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    if ext == ".txt":
        text = content.decode("utf-8", errors="replace").strip()
        if not text:
            raise UnsupportedForExtraction("The uploaded text file is empty.")
        return text

    if ext == ".pdf":
        from pypdf import PdfReader

        reader = PdfReader(io.BytesIO(content))
        text = "\n".join(page.extract_text() or "" for page in reader.pages).strip()
        if not text:
            raise UnsupportedForExtraction(
                "No extractable text found in this PDF (likely scanned/image-only — OCR isn't built)."
            )
        return text

    raise UnsupportedForExtraction(
        f"Extraction from '{ext or filename}' isn't supported yet — only .txt and text-layer .pdf are."
    )