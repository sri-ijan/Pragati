# SetuAI — Project Context

> Repo: https://github.com/sri-ijan/Pragati (repo name "Pragati"; product name "SetuAI").
> This file is updated after EVERY substantial task. `docs/` is updated only at phase boundaries.

## 1. Project Overview

SetuAI is an AI Planning-to-Execution Bridge for SIH Problem Statement 122. Infrastructure projects
keep a structured baseline schedule (Primavera P6 / MS Project, L5/L6 activities), but actual field
progress arrives as DPRs, spreadsheets, site diaries, and verbal updates, written in inconsistent
terminology and granularity. SetuAI ingests that heterogeneous field data, extracts structured
execution events, normalizes terminology, matches events to schedule activities using a hybrid
metadata + semantic + LLM + rules pipeline, scores confidence, routes ambiguous cases to human
review, and — once approved — updates the schedule with a full audit trail.

One-line pitch: *Convert how construction sites naturally report work into trustworthy,
schedule-ready actuals without forcing supervisors to learn another reporting system.*

## 2. Problem Statement

SIH PS 122 — AI-Powered Field-to-Schedule Reconciliation. Full framing, goals and non-goals are in
`plan.md` §0–§1. Core problem statement: **field evidence → L5/L6 semantic reconciliation.**

## 3. Current MVP Scope

Not yet implemented — planning phase only (see §13). Scoped P0 feature set per `plan.md` §36:

- Schedule ingestion (Excel)
- DPR ingestion (PDF/text)
- Structured extraction (LLM → schema-validated JSON)
- Semantic matching (hard filter → embeddings retrieval → LLM rerank → deterministic validation)
- Confidence scoring (weighted composite, configurable thresholds)
- Review queue (approve / correct / unmatched)
- Schedule update (actual_start/actual_finish, audit trail)
- Audit trail

P1 (build if P0 is solid): Dashboard, Historical memory (institutional memory / project memory query).
P2/P3 (cut first if time is short): Voice interface, OCR, real P6 integration (mock/API boundary
only), forecasting, computer vision, blockchain, AR/VR.

## 4. Non-Goals

Per `plan.md` §1: not a full Primavera replacement, no production-grade OCR/ASR, no full
construction ERP/PMIS, no computer vision from site cameras, no drone/BIM/digital-twin platform,
no autonomous schedule replanning, no production-grade delay forecasting, no enterprise-grade
identity/security, no nationwide deployment.

## 5. Current Architecture

Frontend: React / Next.js, Tailwind CSS, Recharts or ECharts (voice UI optional, later).
Backend: Python, FastAPI, Pydantic.
Data processing: Pandas, openpyxl, PyMuPDF/pdfplumber; OCR only if genuinely needed.
AI: LLM for structured extraction + candidate reasoning; embeddings for semantic retrieval;
optional small classifier/reranker only if enough labelled examples exist.
Database: PostgreSQL with pgvector for embeddings.
Storage: TBD (source documents — likely object storage or local disk for MVP; decide in Slice 0).
External integrations: none for MVP — schedule export is the system of record; expose an
integration-ready API boundary rather than faking a live Primavera/PMIS connection (`plan.md` §14, §29 Q4).

Deployment (hackathon-grade, avoid infra rabbit holes): Frontend on Vercel-equivalent, backend on
Render/Railway-equivalent, DB on a hosted Postgres service.

## 6. Repository Structure

Not yet created. Target layout (adapt to actual stack once Slice 0 is done):

```text
setuai/  (repo: Pragati)
├── frontend/
│   ├── app/              (layout.tsx, page.tsx — owns projectId state, globals.css)
│   ├── components/
│   │   ├── ProjectCreateForm.tsx    ← project creation, shared by both upload forms
│   │   ├── ScheduleUploadForm.tsx   ← Slice 1, takes projectId as a prop, reloads on mount
│   │   └── FieldUpdateForm.tsx      ← Slice 2 intake + Slice 3 Extract + Slice 4 "Find
│   │                                   schedule matches" (top-3 candidates, no approve/reject yet)
│   ├── hooks/            (empty)
│   ├── services/
│   │   └── apiClient.ts   ← + matchEvent, getCandidates (Slice 4)
│   ├── types/
│   │   └── shared.ts      ← re-exports shared/types.ts, don't redefine types locally
│   ├── utils/            (empty)
│   ├── package.json, tsconfig.json, next.config.js, tailwind.config.js, postcss.config.js
│
├── backend/
│   ├── api/
│   │   ├── health.py       ← GET /health, GET /health/db
│   │   ├── projects.py     ← POST /projects
│   │   ├── schedule.py     ← POST/GET schedule upload (Slice 1)
│   │   ├── documents.py    ← POST upload + GET list, field documents (Slice 2)
│   │   ├── extraction.py   ← POST /extract, GET /events (Slice 3)
│   │   └── matching.py     ← POST /events/{id}/match, GET /events/{id}/candidates (Slice 4)
│   ├── config/
│   │   ├── settings.py     ← + gemini_embedding_model (Slice 4)
│   │   └── database.py     ← SQLAlchemy engine + get_db dependency
│   ├── services/
│   │   ├── schedule_parser.py         ← Excel/CSV → ScheduleActivity (Slice 1)
│   │   ├── document_storage.py        ← writes uploads to data/uploads/ (Slice 2)
│   │   ├── llm_provider.py            ← LLMProvider interface (extract_fields + Slice 4's
│   │   │                                 rerank_candidates) + GroqLLMProvider (primary) +
│   │   │                                 GeminiLLMProvider (fallback) — no Anthropic
│   │   ├── embeddings_provider.py     ← Gemini-only (Groq has no embeddings API) (Slice 4)
│   │   ├── document_text_extractor.py ← .txt/.pdf → plain text (Slice 3)
│   │   ├── extraction_service.py      ← orchestration + validation (Slice 3)
│   │   └── matching_service.py        ← hard filter → semantic retrieval → LLM rerank →
│   │                                     deterministic scoring → confidence (Slice 4)
│   ├── repositories/
│   │   ├── project_repository.py
│   │   ├── schedule_repository.py
│   │   ├── document_repository.py
│   │   ├── execution_event_repository.py  ← + get_event_by_id (Slice 4)
│   │   ├── embedding_repository.py        ← pgvector cache + real cosine-distance query (Slice 4)
│   │   └── match_repository.py            ← replace-not-accumulate per event (Slice 4)
│   ├── models/
│   │   ├── schemas.py      ← Slice 0 canonical contracts (locked, untouched)
│   │   └── orm.py          ← ProjectORM, ScheduleActivityORM, SourceDocumentORM,
│   │                          ExecutionEventORM, ActivityEmbeddingORM, ActivityMatchORM (Slice 4)
│   ├── tests/               ← 53 pytest tests total (27 new in Slice 4) — see test_matching_*.py,
│   │                          test_embedding_repository_pgvector.py (real Postgres, self-skips),
│   │                          test_embeddings_provider.py, test_match_repository.py
│   ├── main.py               ← FastAPI app, all routers wired, pgvector extension creation,
│   │                            error envelope
│   ├── requirements.txt      ← + pgvector (Slice 4)
│   └── requirements-dev.txt  ← pytest, httpx — test-only, not shipped (Slice 3)
│
├── shared/
│   └── types.ts             ← Slice 0 canonical contracts (locked, untouched)
├── data/
│   └── uploads/              ← local-disk file storage (gitignored, not the dataset itself)
├── docs/       (PRD, ARCHITECTURE, DESIGN, ROADMAP, API, DECISIONS)
├── tests/      (backend tests live under backend/tests/ instead — see above)
├── plan.md
├── context.md
├── README.md
├── .env.example
├── .gitignore
└── package.json (root — not yet needed; each of frontend/backend has its own dependency file)
```

`shared/types.ts` and `backend/models/schemas.py` remain the source of truth for every domain type
and API shape — untouched by the Slice 1-prep scaffolding above. Keep them in sync by hand; log any
change in `docs/DECISIONS.md`.

## 7. Core Data Flow

```text
Schedule Excel + DPR/spreadsheet/text
      ↓ Ingestion (parse, normalize dates/case/units)
Canonical Event / Schedule Activity records
      ↓ LLM Extraction (schema-constrained, evidence-preserving)
Execution Event (structured)
      ↓ Terminology Normalization (growing dictionary, reviewer-corrected)
      ↓ Candidate Retrieval — Stage 1: hard filter (discipline/area/WBS/line/tag/date/status)
      ↓ Stage 2: semantic retrieval (embeddings, top-K 5–10)
      ↓ Stage 3: LLM reranking (action/object/location/discipline/tags/temporal/granularity)
      ↓ Stage 4: deterministic validation (reject impossible matches)
Confidence Engine (weighted composite score)
      ↓
   AUTO-MATCH (≥0.90) | REVIEW REQUIRED (0.70–0.89) | UNMATCHED (<0.70)
      ↓
Human Review (approve / correct / mark unmatched)
      ↓
Schedule Update (actual_start/actual_finish) + Audit Trail entry
      ↓
Analytics Dashboard + Institutional Memory (historical stats, natural-language query)
```

## 8. Data Models — FINALIZED (Slice 0, 2026-09-15)

Canonical schemas are fixed by `plan.md` §6 and implemented as real typed contracts, not just
prose:

- `shared/types.ts` — TypeScript, for the frontend.
- `backend/models/schemas.py` — Pydantic, for the backend.

Both define: `ExecutionEvent`, `ScheduleActivity`, `MatchRecord`, `AuditLogEntry`, `Project`, the
`Discipline`/`EventStatus`/`MatchDecision`/`ReviewAction` enums, the confidence weights/thresholds,
and every endpoint request/response shape. Treat these two files as canonical; this section is a
pointer, not a duplicate — don't let a third informal definition of these types appear anywhere
else in the codebase.

Minimum DB tables (`plan.md` §23): projects, schedule_activities, source_documents,
execution_events, activity_matches, review_decisions, audit_logs, terminology,
historical_activity_stats. Optional: activity_embeddings, contractors, delay_causes.

## 9. API Contracts — FINALIZED (Slice 0, 2026-09-15)

Full endpoint list, request/response shapes, auth decision (none for MVP), file storage decision
(local disk under `data/uploads/`), upload constraints, and error envelope are all in
`docs/API.md`. Routes not implemented yet — only the contract is locked. Endpoint list:

```text
POST /projects
POST /projects/{id}/schedule/upload
POST /projects/{id}/documents/upload
POST /projects/{id}/extract
GET  /projects/{id}/events
POST /events/{id}/match
GET  /events/{id}/candidates
POST /matches/{id}/approve
POST /matches/{id}/correct
POST /matches/{id}/reject
GET  /projects/{id}/schedule
GET  /projects/{id}/analytics
GET  /projects/{id}/audit-log
POST /projects/{id}/memory/query
```

## 10. AI Pipeline

Matching pipeline (do not simplify — this is the product's core differentiator, `plan.md` §10,
§18, §31):

1. **Hard filter** on discipline, area, WBS, line number, equipment tag, date, activity status.
2. **Semantic retrieval**: embeddings over field event + activity descriptions, top-K 5–10.
3. **LLM rerank**: evaluate action/object/location/discipline/tags/temporal compatibility/granularity
   on the filtered candidate set only.
4. **Deterministic validation**: reject/penalize impossible matches (discipline mismatch, explicit
   line mismatch, incompatible status transitions, out-of-window dates, e.g. hydrotest event mapped
   to erection activity).

Confidence formula (`plan.md` §11 — prototype weights, configurable, not scientifically validated;
say so plainly if asked):

```text
final_confidence =
    0.35 × semantic_score
  + 0.25 × metadata_score
  + 0.20 × llm_rerank_score
  + 0.10 × temporal_score
  + 0.10 × terminology_score
```

Thresholds: ≥0.90 auto-match, 0.70–0.89 review required, <0.70 unmatched. Log every component
score, not just the final number — this is what makes the "matched because ✓✓✓" explainability UI
possible (`plan.md` §12).

LLM extraction must be schema-constrained (never free-form), must never invent an activity ID or
infer an unsupported completion date, and must preserve raw evidence text (`plan.md` §8).

No deviation from this pipeline has been made yet. (Flag here if a deviation ever becomes
necessary, with reason.)

## 11. UI Architecture

Target pages (`plan.md` §21): Project Dashboard, Upload Center, Extraction (events + evidence),
Matching (top candidates + confidence), Review Queue (approve/correct/unmatched), Schedule
(planned vs actual), Analytics, Project Memory (NL query over history). Demo flow drives priority —
see §19 below. Not yet built.

## 12. Important Design Decisions

| Decision | Reason | Alternatives rejected |
|---|---|---|
| Product name SetuAI, repo name stays "Pragati" | Repo was already created before naming settled; renaming later is low-cost, not worth blocking on now | Renaming the GitHub repo immediately |
| Hybrid matching (metadata + embeddings + LLM rerank + rules), never "LLM decides and writes directly" | `plan.md` §28/§31: a hallucinated direct match can corrupt project controls; this is the single biggest technical risk | Pure LLM-to-activity-ID pipeline |
| Confidence is a weighted composite, not raw LLM confidence | Raw LLM confidence is not trustworthy for a matching decision (`plan.md` §11) | Using LLM's self-reported confidence directly |
| No real Primavera/PMIS integration for MVP; expose an integration-ready API boundary instead | Avoid faking a production integration (`plan.md` §14, §29 Q4) | Building a mock that pretends to be live P6 sync |
| Full-scale synthetic dataset (~300 activities / ~150 events) generated with AI assistance, not scaled down | Master prompt §22 — scope decided explicitly; a small dataset can't stress-test the matching engine's actual differentiator | Shrinking the dataset to save time |

## 13. Current Implementation Status

**DONE:** Problem/product decided (SetuAI, PS 122), `plan.md` written, GitHub repo created
(`sri-ijan/Pragati`, initially empty except `.gitignore`, `LICENSE`, `README.md`), `context.md` and
`docs/` set created. Slice 0 complete: shared contracts (`shared/types.ts`,
`backend/models/schemas.py`), finalized `docs/API.md`. Slice 1 scaffolding complete (FastAPI +
Next.js skeletons, health checks verified).

**Slice 1 feature work complete**: schedule upload end-to-end, verified against a real local
Postgres instance in the build sandbox (not just unit-level):
- `backend/models/orm.py` — `ProjectORM`, `ScheduleActivityORM` (first real tables:
  `projects`, `schedule_activities`; created via `Base.metadata.create_all()` at startup, not
  Alembic — see `docs/DECISIONS.md`).
- `backend/services/schedule_parser.py` — Excel/CSV parser, column-synonym header matching,
  per-row validation with warnings (a bad row is skipped, not fatal to the batch).
- `backend/repositories/project_repository.py`, `schedule_repository.py` — DB access, dedup on
  re-upload (existing `activity_id`s for a project are skipped, not duplicated).
- `backend/api/projects.py` (`POST /projects`), `backend/api/schedule.py` (`POST
  /projects/{id}/schedule/upload`, `GET /projects/{id}/schedule`), wired into `main.py` with a
  global exception handler normalizing every error to the `docs/API.md` envelope.
- `frontend/components/ScheduleUploadForm.tsx` — create project → upload file → shows imported
  count, warnings, activity table; wired into `app/page.tsx`.
- `frontend/services/apiClient.ts` — `createProject`, `uploadSchedule`, `getSchedule` added.

**Verified in the sandbox** (real Postgres, real `.xlsx` with deliberately bad rows): project
creation, successful import (3/5 rows, 2 bad rows correctly rejected with warnings), re-upload
dedup (0 re-inserted, flagged as duplicates), bad file type → 422 with correct error envelope,
unknown project → 404 with correct error envelope, CORS headers correct for the frontend origin,
`npm run build` type-checks clean. One real bug found and fixed during verification: a `.scalars()`
call on a single-column SQLAlchemy query was misread as row objects — logged in `docs/DECISIONS.md`.

**IN PROGRESS:** Nothing — Slice 2 (field report input) is functionally complete.

**Slice 2 feature work complete**: field report/document intake end-to-end, verified against real
Postgres + real local-disk storage:
- `backend/models/orm.py` — added `SourceDocumentORM` (`source_documents` table).
- `backend/services/document_storage.py` — writes uploads to
  `data/uploads/{project_id}/{source_document_id}/{filename}`; filename sanitized (basename only)
  to prevent path traversal from a crafted filename.
- `backend/repositories/document_repository.py` — create + list, newest-first.
- `backend/api/documents.py` — `POST /projects/{id}/documents/upload` (contracted) and `GET
  /projects/{id}/documents` (**new — added to `docs/API.md`, logged in `docs/DECISIONS.md`, not a
  silent contract change**). Accepts `.pdf/.txt/.docx/.xlsx/.csv/.jpg/.jpeg/.png`; images accepted
  but flagged `processable_now: false` (OCR is P2, not built).
- `backend/config/settings.py` — `max_upload_bytes` and `uploads_dir` centralized here; `schedule.py`
  refactored to use the shared setting instead of its own duplicate constant.
- `frontend/components/FieldUpdateForm.tsx` — typed text (wrapped client-side as a `.txt` upload,
  same endpoint/contract, no separate "text update" API shape) or file upload, lists submissions.
- `frontend/components/ProjectCreateForm.tsx` — project creation extracted out of
  `ScheduleUploadForm` so one project can be shared by both the schedule and field-update forms;
  `app/page.tsx` now owns `projectId` state and renders both forms once a project exists.

**Verified in the sandbox**: valid `.txt` upload accepted + `processable_now: true`; `.png` accepted
+ correctly flagged `processable_now: false`; `.exe` rejected with `422` and the documented error
envelope; list endpoint returns newest-first; unknown project → `404`; files land on disk at the
exact contracted path; `npm run build` still type-checks clean after the `ScheduleUploadForm`
refactor.

**Interim frontend fixes (not separately logged at the time, noted here for accuracy):**
`projectId` now persists in `localStorage` and restores on page load (`app/page.tsx`);
`ScheduleUploadForm.tsx` reloads the existing schedule on mount instead of requiring re-upload after
a refresh; the "Load submitted updates" button in `FieldUpdateForm.tsx` is now always visible
instead of hiding itself once any document exists (was a genuine regression, not intentional).

**IN PROGRESS:** Nothing — Slice 3 (AI extraction) is functionally complete, scope-limited exactly
as instructed (extraction only, no matching/reranking/confidence/review/schedule-update/audit-trail).

**Slice 3 feature work complete**: field evidence → schema-constrained LLM extraction → validated
`ExecutionEvent` → persisted → exposed via API → shown in frontend, end to end:
- `backend/services/llm_provider.py` — `LLMProvider` abstract interface; **Groq is the primary
  provider, Gemini is the automatic fallback** (no Anthropic anywhere — swapped out right after the
  initial Slice 3 build per instruction). Fallback triggers only on `LLMProviderUnavailable` (rate
  limit/quota/connection/5xx) — never merely because output looked wrong. `get_llm_provider()`
  raises `LLMProviderNotConfigured` only when neither `GROQ_API_KEY` nor `GEMINI_API_KEY` is set —
  verified over real HTTP to fail with a clean `503`, nothing persisted, no fake output.
- `backend/services/document_text_extractor.py` — `.txt` (direct) and `.pdf` (text-layer, `pypdf`,
  no OCR) only; anything else raises `UnsupportedForExtraction` cleanly.
- `backend/services/extraction_service.py` — orchestration + validation, **unchanged by the
  provider swap** (it only ever depended on the generic `LLMProvider` interface). Two flagged
  judgment calls here, full reasoning in `docs/DECISIONS.md`: (1) `event_date` falls back to the
  source document's real upload date when the LLM found no explicit date (never invented by either
  LLM); (2) any other required field the LLM can't determine causes a clean `422
  EXTRACTION_INCOMPLETE` rather than a guess.
- `backend/models/orm.py` — added `ExecutionEventORM` (`execution_events` table), additive only.
- `backend/repositories/execution_event_repository.py` — save + list, project-scoped, optional
  status filter.
- `backend/api/extraction.py` — `POST /projects/{id}/extract`, `GET /projects/{id}/events`, both
  already contracted in `docs/API.md` from Slice 0 (no new contract surface needed this time),
  **unchanged by the provider swap** (same reason as extraction_service.py above).
- `backend/api/documents.py` — `processable_now` now derived from
  `document_text_extractor.EXTRACTABLE_EXTENSIONS` instead of an image-only exclusion list, so it
  stays honest about `.docx`/`.xlsx`/`.csv` not being extractable yet either.
- `frontend/components/FieldUpdateForm.tsx` — an "Extract" button per processable document, showing
  a clearly-separated "AI-extracted structured event" card (amber background) below the raw
  evidence text — visually distinct from the plain document list, no matching UI. Frontend has zero
  provider-specific code, so it also needed no changes for the provider swap.
- `backend/tests/` — 26 automated tests (pytest; grew from 16 to 26 with the provider swap — see
  below), a `FakeLLMProvider`/`_SpyProvider` used only in tests (never as the runtime path), real
  SQLite persistence tests, real regression tests that Slice 1/2 endpoints still wire correctly.

**Verified**: all 26 tests pass (12 of them specifically about provider selection/fallback,
including: Groq success means Gemini is never called; a Groq availability failure triggers Gemini;
both failing raises the same error type `api/extraction.py` already handled; a non-availability
Groq failure does *not* trigger fallback; API keys never appear in any exception message or
provider object); real end-to-end HTTP test against live Postgres confirmed the missing-provider
path fails cleanly (503, message now naming `GROQ_API_KEY`/`GEMINI_API_KEY`, nothing persisted);
`npm run build` clean. **Not verified**: an actual live Groq or Gemini API call — no key for either
is available in the build sandbox, none fabricated.

**IN PROGRESS:** Nothing — Slice 4 (matching engine) is functionally complete.

**Slice 4 feature work complete**: hard filter → semantic retrieval (Gemini embeddings + pgvector)
→ LLM reranking (reuses the Slice 3 `LLMProvider` boundary) → deterministic scoring → weighted
confidence → persisted `MatchRecord`s, end to end:
- `backend/services/embeddings_provider.py` — `EmbeddingsProvider` interface + `GeminiEmbeddingsProvider`
  (Gemini only — Groq has no embeddings API, so no fallback pair exists here). Raises
  `EmbeddingsProviderNotConfigured` clearly when `GEMINI_API_KEY` is unset.
- `backend/services/llm_provider.py` — extended with `rerank_candidates`, sharing the exact same
  Groq-primary/Gemini-fallback policy as `extract_fields` via a refactored generic
  `_call_with_fallback` helper (no duplicated fallback logic between the two capabilities).
- `backend/services/matching_service.py` — the pipeline itself. `terminology_score` is now a real
  field on `MatchRecord` (resolved 2026-09-24, Option B — see `docs/DECISIONS.md`; the locked
  `CONFIDENCE_WEIGHTS` formula's `terminology` component is fully exposed, not just folded into
  `final_confidence`).
- `backend/repositories/embedding_repository.py` — caches embeddings per activity; the actual
  semantic retrieval is a real pgvector cosine-distance SQL query, not Python-side comparison.
- `backend/repositories/match_repository.py` — a fresh match run **replaces** the previous batch
  for that event (delete + insert), no match-run history kept.
- `backend/api/matching.py` — `POST /events/{id}/match`, `GET /events/{id}/candidates`, both
  already contracted in `docs/API.md` from Slice 0.
- `backend/models/orm.py` — added `ActivityEmbeddingORM` (pgvector `Vector(768)` column) and
  `ActivityMatchORM`, additive only. `main.py`'s startup now also runs `CREATE EXTENSION IF NOT
  EXISTS vector` before `create_all()`, same non-blocking-if-DB-down pattern as table creation.
- `frontend/components/FieldUpdateForm.tsx` — a "Find schedule matches" button per extracted event,
  showing top-3 candidates with confidence % and reasons — no approve/correct/reject actions
  (that's Slice 5).
- `backend/tests/` — 53 tests total (27 new): pure scoring-function tests, mocked orchestration
  tests (no real DB/providers needed), real-Postgres pgvector tests (self-skip if Postgres/vector
  extension unreachable), embeddings-provider config tests, match-persistence tests.

**Verified**: all 53 tests pass. Real end-to-end HTTP verification against live Postgres+pgvector:
no keys configured → clean `503 EMBEDDINGS_PROVIDER_NOT_CONFIGURED`; with placeholder (invalid)
keys, the pipeline correctly reached the real Gemini embeddings API call and surfaced a clean `502
EMBEDDINGS_FAILED` — this also revealed the build sandbox's network egress doesn't allowlist
Gemini/Groq's actual API hosts, so a genuine successful live call couldn't be verified here (a
sandbox limitation, not a code issue). One real bug found and fixed: `match_repository.replace_matches`
was trusting `match.event_id` from the object instead of its own `event_id` parameter — caught by a
test, not a read-through. `npm run build` clean.

**TODO:** Slice 5 (review queue + approval + schedule update + audit trail). See `docs/ROADMAP.md`.
`GEMINI_API_KEY` specifically is required for matching (embeddings) even if extraction is running
on Groq alone — `GROQ_API_KEY` and/or `GEMINI_API_KEY` need to be set in your real `.env` before
either extraction or matching can actually run end-to-end outside this sandbox.

## 14. Who's Working On What (Live)

**Solo development.** Per explicit instruction, this project is not being parallelized across
tracks/roles right now — one person (with an AI coding assistant) working sequentially, one task
at a time. The Master Engineering Prompt's §7 (6-person coordination) and the track table in
`docs/ROADMAP.md` describe the *original* team-of-6 plan and stay in the docs for reference, but do
not currently apply — don't wait on or reference "other tracks" while solo. If the team
reconvenes and parallelizes later, revive this table then.

**Current focus:** Slice 3 (AI extraction, Groq/Gemini) just completed — see §13. Nothing in
progress. Next up on go-ahead: Slice 4 (matching engine).

## 15. Known Issues

- No automated test suite exists for Slice 1/2 endpoints specifically (schedule upload, document
  upload/list) — only Slice 3 (extraction) has pytest coverage so far. Slice 1/2 were verified
  manually/end-to-end in the build sandbox, not via repeatable CI.
- No live LLM call (Groq or Gemini) has actually been exercised — no API key has been available in
  the build sandbox for either provider. Only the "neither configured" failure path and
  deterministic-mock-based extraction logic have been verified for real.
- Biggest real risk still ahead, unchanged from the original assessment: semantic matching accuracy
  once Slice 4 starts (`plan.md` §31) — bigger than any UI/parsing/LLM-call/dashboard concern.

## 16. Environment Variables

Defined in `.env.example` (root) — copy to `.env` for local dev, never commit it. Names only, no
values beyond safe local-dev defaults:

- `DATABASE_URL` — Postgres connection string (backend).
- `APP_ENV` — `development` / `production` (backend).
- `BACKEND_PORT` — port the FastAPI app runs on.
- `FRONTEND_ORIGIN` — origin allowed by backend CORS in dev.
- `NEXT_PUBLIC_API_URL` — backend base URL the frontend calls.
- `GROQ_API_KEY` — **primary provider** for extraction (Slice 3, revised). Without either this or
  `GEMINI_API_KEY`, `POST /projects/{id}/extract` fails cleanly with `503
  LLM_PROVIDER_NOT_CONFIGURED` — intentional, not a bug, per the "never fake AI output" rule. Not
  yet set anywhere real — add your own key to `.env`.
- `GROQ_MODEL` — optional, overrides the default `openai/gpt-oss-20b` (needed for Groq's strict
  structured-output mode).
- `GEMINI_API_KEY` — **automatic fallback provider** for extraction/reranking, used only when Groq
  fails for an availability reason (rate limit/quota/connection/5xx) — not merely because output
  looked wrong. Works alone too if `GROQ_API_KEY` isn't set (treated as Groq-unavailable, falls
  through to Gemini immediately). **Also required for matching** (Slice 4) regardless of which
  provider handles extraction/reranking — Groq has no embeddings API, so semantic retrieval always
  needs this key specifically.
- `GEMINI_MODEL` — optional, overrides the default `gemini-2.5-flash`.
- `GEMINI_EMBEDDING_MODEL` — optional, overrides the default `gemini-embedding-001` (Slice 4).

No Anthropic variable exists anywhere in this project — removed entirely per instruction.

## 17. How to Run

**Backend** (from `backend/`):

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp ../.env.example ../.env   # then edit ../.env — set GROQ_API_KEY and/or GEMINI_API_KEY for
                              # extraction to work, and check DATABASE_URL if your local Postgres differs
.venv/bin/uvicorn main:app --reload --port 8000
```

Verify: `curl http://localhost:8000/health` → `{"status":"ok",...}`. `GET /health/db` reports
Postgres connectivity without crashing the app if the DB isn't up yet.

**Backend tests** (from `backend/`, after the venv above exists):

```bash
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/python -m pytest tests/ -v
```

16 tests, no Postgres or real LLM key required — persistence tests use an in-memory SQLite session,
extraction-logic tests use a deterministic fake provider (test-only, never the runtime path).

**Frontend** (from `frontend/`):

```bash
npm install
npm run dev
```

Verify: open `http://localhost:3000` → SetuAI placeholder page.

No `docker-compose` / one-command bootstrap yet — add one if it starts saving real time; not worth
the setup cost for a two-service, single-developer MVP right now.

## 18. How to Test

Not yet defined — will be filled in once ingestion and extraction exist (Slice 2/3).

## 19. Demo Flow

Exact sequence to rehearse (`plan.md` §33, "Killer Demo" — do not deviate):

1. Upload schedule → "1,248 L5/L6 activities imported" (use the actual dataset count once built).
2. Upload DPR → e.g. "Piping crew completed erection of 24-inch spool at Rack B."
3. AI extraction shown on screen: discipline, action, object, location, status.
4. Matching: show top-3 candidates with confidence (e.g. PIP-101 94%, PIP-102 63%, PIP-113 28%).
5. Explainability: ✓ same discipline, ✓ same location, ✓ same line, ✓ same action, ✓ compatible date.
6. Approve → Actual Finish updates.
7. Schedule variance shown: baseline vs actual, e.g. "+2 days."
8. Historical insight: e.g. "Similar piping activities historically exceeded planned duration by
   1.4 days."
9. Closing line: "From field language to schedule-ready actuals in seconds."

Likely judge challenge to be ready for: showing top-3 matches instead of just the winner
(`plan.md` §30) — the UI must already support this, not be bolted on live.

## 20. Next Recommended Task

Slices 1-4 (schedule upload, field document intake, AI extraction, matching engine) are
functionally complete and verified. **Next: Slice 5** — review + approval: `POST
/matches/{id}/approve`, `/correct`, `/reject` (all already contracted in `docs/API.md`), a
`review_decisions` table, updating the schedule activity's `actual_start`/`actual_finish` on
approval, and an `audit_logs` entry for every decision (`plan.md` §20 — auditability). Frontend:
the reviewer screen `docs/DESIGN.md` describes (approve/correct/unmatched actions on top of the
top-3 candidates Slice 4 already shows) — this is the first slice that actually writes back to
`schedule_activities`, so double-check the "never let uncertain AI predictions silently modify
data" rule stays intact (only an explicit human action should call `/approve`). Real
`GEMINI_API_KEY` (and ideally `GROQ_API_KEY`) should be set before this lands, so the whole
extract → match → review loop can be tried live for the first time, end to end, outside this
sandbox's network restrictions.

## 21. Handoff Notes

- Repo `sri-ijan/Pragati` now has a working backend (FastAPI) and frontend (Next.js) through Slice 3
  — schedule upload, field document intake, and AI extraction are all implemented and verified. It
  started as a from-scratch build (repo was empty except `.gitignore`/`LICENSE`/`README.md`); it
  is no longer empty — check §13 for exactly what exists before assuming anything is missing.
- `plan.md` (the product/technical spec) is authoritative for anything product/technical; this
  `context.md` and the Master Engineering Prompt govern process only. See `plan.md` §0 priority order
  in §36 of the Master Prompt if anything conflicts.
- Do not simplify the matching pipeline (§10 above) or shrink the dataset target (~300 activities /
  150 events / 4 disciplines / 3 formats / 30+ ambiguous cases across all 7 edge-case categories) to
  save time. If time runs short, cut voice/OCR/real-P6-integration first — never the matching engine,
  review workflow, or audit trail (`plan.md` §25, §36).
- Before starting any task: read this file's §14 to see what teammates' AI sessions are doing.
  Update §14 immediately when you start or pause work, even mid-task.