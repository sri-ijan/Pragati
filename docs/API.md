# SetuAI — API Contracts

Status: **Slice 0 finalized.** Canonical types live in `shared/types.ts` (frontend) and
`backend/models/schemas.py` (backend) — those two files are the actual source of truth; this
document explains how they're used. If either file changes, change the other, update this doc, and
log the change in `docs/DECISIONS.md`.

## Naming Conventions

- JSON fields: `snake_case`, matching the Python/DB field names exactly — no camelCase remapping
  at the API boundary.
- Dates: ISO-8601 (`YYYY-MM-DD`); datetimes: ISO-8601 with timezone (`YYYY-MM-DDTHH:MM:SSZ`).
- IDs: strings. Activity IDs follow the schedule source's own scheme (e.g. `PIP-101`); generated
  IDs (`event_id`, `audit_id`, etc.) are prefixed (`EVT-`, `AUD-`, `SRC-`, `MATCH-`).
  `event_date`/dates on the wire only — no locale-formatted display in API responses.
- Routes: REST, resource-based, plural nouns, per the endpoint list below.

## Auth (MVP decision)

No auth for the hackathon MVP — all endpoints open, no login flow. Every write endpoint that
records a `reviewer` takes it as a plain string field in the request body (typed name, not a
session identity). This is a deliberate hackathon-scope simplification, not a security stance —
flag it as such if judges ask (`plan.md` §1 non-goals: no enterprise-grade identity/security).

## File Storage (MVP decision)

Uploaded files (`schedule.xlsx`, DPRs, discipline spreadsheets) are stored on local disk under
`data/uploads/{project_id}/{source_document_id}/{original_filename}` for the MVP. Production would
move this to object storage (S3-equivalent) — noted here, not built.

## Upload Constraints

- Schedule upload: `.xlsx`, `.xls`, `.csv`; max 10 MB.
- Document upload (DPR / discipline spreadsheet): `.pdf`, `.txt`, `.docx`, `.xlsx`, `.csv`; max
  10 MB. Image upload (`.jpg`/`.png`) is accepted at the API level per `plan.md`'s "optionally a
  simple image" note, but OCR extraction from it is P2/optional — an uploaded image may sit
  unprocessed until that's built.

## Error Shape

Every non-2xx response returns:

```json
{
  "error": {
    "code": "SCHEDULE_PARSE_ERROR",
    "message": "Row 14 is missing a required column: Planned Finish",
    "details": { "row": 14, "column": "Planned Finish" }
  }
}
```

`code` is a stable machine-readable string (`NOT_FOUND`, `VALIDATION_ERROR`,
`SCHEDULE_PARSE_ERROR`, `EXTRACTION_FAILED`, `LLM_ERROR`, etc.) the frontend can switch on;
`message` is human-readable; `details` is optional structured context.

## Canonical Schemas

See `shared/types.ts` / `backend/models/schemas.py` for the authoritative definitions. Summary:

### Execution Event

```json
{
  "event_id": "EVT-001",
  "source_id": "DPR-2026-09-08-01",
  "discipline": "Piping",
  "activity_description": "24-inch spool erection",
  "action": "erection",
  "status": "completed",
  "location": "Rack B",
  "equipment_tag": null,
  "line_number": "24-XX",
  "event_date": "2026-09-08",
  "quantity": null,
  "unit": null,
  "raw_text": "Piping crew completed erection...",
  "confidence": null
}
```

### Schedule Activity

```json
{
  "activity_id": "PIP-101",
  "wbs": "PIP-A",
  "discipline": "Piping",
  "description": "Erect Line 24-XX at Rack B",
  "area": "Rack B",
  "planned_start": "2026-09-01",
  "planned_finish": "2026-09-04",
  "actual_start": null,
  "actual_finish": null
}
```

### Match Record

```json
{
  "event_id": "EVT-001",
  "candidate_activity_id": "PIP-101",
  "semantic_score": 0.91,
  "metadata_score": 0.95,
  "temporal_score": 0.90,
  "llm_score": 0.95,
  "final_confidence": 0.94,
  "decision": "auto_match",
  "reviewer": null,
  "reason": [
    "Same discipline",
    "Same location",
    "Same line number",
    "Same execution action",
    "Compatible schedule window"
  ]
}
```

## Endpoints

### `POST /projects`
Create a project. **Request:** `{ "name": string }`. **Response:** `Project`.

### `POST /projects/{id}/schedule/upload`
Multipart file upload (`.xlsx`/`.xls`/`.csv`). Parses into `ScheduleActivity` rows.
**Response:** `UploadScheduleResponse`.

### `POST /projects/{id}/documents/upload`
Multipart file upload (DPR / discipline spreadsheet / text / image). Stores the file on disk under
`data/uploads/{project_id}/{source_document_id}/{filename}` and a `source_documents` row; does not
extract yet. Accepted types: `.pdf`, `.txt`, `.docx`, `.xlsx`, `.csv`, `.jpg`, `.jpeg`, `.png`
(images are accepted but flagged `processable_now: false` until OCR exists — P2 per `plan.md`).
**Response:** `UploadDocumentResponse`.

### `GET /projects/{id}/documents` — *added in Slice 2, not in the original Slice 0 list*
Lists a project's `source_documents`, newest first. Added because Slice 2 needed some way to see
what had been uploaded (mirrors `GET /projects/{id}/schedule`, which was already contracted) — see
`docs/DECISIONS.md` for the reasoning. **Response:** array of `{ source_document_id, filename,
content_type, status, uploaded_at, processable_now }`.

### `POST /projects/{id}/extract`
Runs LLM extraction on a given `source_document_id` (passed in body) into one or more
`ExecutionEvent`s. **Request:** `{ "source_document_id": string }`. **Response:** `ExtractResponse`.

### `GET /projects/{id}/events`
List `ExecutionEvent`s for a project. Supports `?status=` filter.

### `POST /events/{id}/match`
Runs the 4-stage matching pipeline for one event. **Response:** `MatchResponse` (candidates sorted
by `final_confidence` desc; UI shows top-3 minimum).

### `GET /events/{id}/candidates`
Re-fetch the last computed `MatchResponse` for an event without recomputing.

### `POST /matches/{id}/approve`
**Request:** `ReviewDecisionRequest` with `action: "approve"`. Applies the top candidate, updates
the schedule activity's `actual_start`/`actual_finish`, writes an `AuditLogEntry`.

### `POST /matches/{id}/correct`
**Request:** `ReviewDecisionRequest` with `action: "correct"` and `corrected_activity_id` set.
Applies the reviewer-selected activity instead of the top candidate; writes an `AuditLogEntry` and
feeds the correction back into the terminology dictionary (`plan.md` §9).

### `POST /matches/{id}/reject`
**Request:** `ReviewDecisionRequest` with `action: "reject"`. Marks the event `unmatched`; no
schedule change; still logged.

### `GET /projects/{id}/schedule`
Full current schedule (planned vs actual) for the project.

### `GET /projects/{id}/analytics`
**Response:** `AnalyticsSummary`.

### `GET /projects/{id}/audit-log`
List of `AuditLogEntry`, newest first. Supports `?event_id=` filter.

### `POST /projects/{id}/memory/query`
Natural-language query over `historical_activity_stats`. **Request:** `{ "query": string }`.
**Response:** shape TBD when Phase 8 (Institutional Memory) starts — not blocking Slice 0.

## Confidence Formula

```text
final_confidence =
    0.35 × semantic_score
  + 0.25 × metadata_score
  + 0.20 × llm_rerank_score
  + 0.10 × temporal_score
  + 0.10 × terminology_score
```

Thresholds: `>= 0.90` → `auto_match`; `0.70–0.89` → `review_required`; `< 0.70` → `unmatched`.
Single implementation lives in `shared/types.ts` (`decisionForConfidence`) and
`backend/models/schemas.py` (`decision_for_confidence`) — do not reimplement this logic a third
time anywhere else in the codebase.

## Database Tables (minimum)

`projects`, `schedule_activities`, `source_documents`, `execution_events`, `activity_matches`,
`review_decisions`, `audit_logs`, `terminology`, `historical_activity_stats`.
Optional: `activity_embeddings`, `contractors`, `delay_causes`.

## Resolved (was "Open Items" pre-Slice-0)

- Auth: none for MVP (see above).
- Storage: local disk under `data/uploads/` for MVP (see above).
- Upload constraints: set above.
- Error shape: set above.

## Still Open (not blocking — revisit at the relevant phase)

- `POST /projects/{id}/memory/query` response shape (Phase 8).
- Pagination shape for `GET /projects/{id}/events` and `GET /projects/{id}/audit-log` once dataset
  scale (~150 events, growing audit log) makes it necessary.
