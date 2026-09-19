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
│   │   ├── ScheduleUploadForm.tsx   ← Slice 1, takes projectId as a prop
│   │   └── FieldUpdateForm.tsx      ← Slice 2, text or file → documents/upload
│   ├── hooks/            (empty)
│   ├── services/
│   │   └── apiClient.ts   ← createProject, uploadSchedule, getSchedule, uploadDocument, getDocuments
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
│   │   └── documents.py    ← POST upload + GET list, field documents (Slice 2)
│   ├── config/
│   │   ├── settings.py     ← Pydantic settings incl. max_upload_bytes, uploads_dir
│   │   └── database.py     ← SQLAlchemy engine + get_db dependency
│   ├── services/
│   │   ├── schedule_parser.py    ← Excel/CSV → ScheduleActivity (Slice 1)
│   │   └── document_storage.py   ← writes uploads to data/uploads/ (Slice 2)
│   ├── repositories/
│   │   ├── project_repository.py
│   │   ├── schedule_repository.py
│   │   └── document_repository.py
│   ├── models/
│   │   ├── schemas.py      ← Slice 0 canonical contracts (locked, untouched)
│   │   └── orm.py          ← ProjectORM, ScheduleActivityORM, SourceDocumentORM
│   ├── main.py              ← FastAPI app, all routers wired, error envelope
│   └── requirements.txt
│
├── shared/
│   └── types.ts             ← Slice 0 canonical contracts (locked, untouched)
├── data/
│   └── uploads/              ← local-disk file storage (gitignored, not the dataset itself)
├── docs/       (PRD, ARCHITECTURE, DESIGN, ROADMAP, API, DECISIONS)
├── tests/      (not started)
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

**TODO:** Slice 3 (AI extraction) → Slice 4 (matching engine) → Slice 5 (approval). See
`docs/ROADMAP.md`. Still no automated test suite (`tests/`) — verification remains manual/sandbox.

## 14. Who's Working On What (Live)

**Solo development.** Per explicit instruction, this project is not being parallelized across
tracks/roles right now — one person (with an AI coding assistant) working sequentially, one task
at a time. The Master Engineering Prompt's §7 (6-person coordination) and the track table in
`docs/ROADMAP.md` describe the *original* team-of-6 plan and stay in the docs for reference, but do
not currently apply — don't wait on or reference "other tracks" while solo. If the team
reconvenes and parallelizes later, revive this table then.

**Current focus:** Slice 1 scaffolding just completed (see §13). Next: Slice 1 feature work
(schedule upload), sequentially.

## 15. Known Issues

None yet — no code exists. First real risk to watch once building starts: semantic matching
accuracy (`plan.md` §31) — this is the biggest technical risk in the whole project, not UI/parsing/
LLM-calls/dashboard.

## 16. Environment Variables

Defined in `.env.example` (root) — copy to `.env` for local dev, never commit it. Names only, no
values beyond safe local-dev defaults:

- `DATABASE_URL` — Postgres connection string (backend).
- `APP_ENV` — `development` / `production` (backend).
- `BACKEND_PORT` — port the FastAPI app runs on.
- `FRONTEND_ORIGIN` — origin allowed by backend CORS in dev.
- `NEXT_PUBLIC_API_URL` — backend base URL the frontend calls.

Not yet needed (add when the relevant slice lands, per `docs/ROADMAP.md`): an LLM provider API key
(Slice 3, extraction), an embeddings provider API key if different from the LLM provider (Slice 4,
matching).

## 17. How to Run

**Backend** (from `backend/`):

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp ../.env.example ../.env   # then edit ../.env if your local Postgres differs
.venv/bin/uvicorn main:app --reload --port 8000
```

Verify: `curl http://localhost:8000/health` → `{"status":"ok",...}`. `GET /health/db` reports
Postgres connectivity without crashing the app if the DB isn't up yet.

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

Slices 1 and 2 (schedule upload, field document intake) are functionally complete and verified.
**Next: Slice 3** — AI extraction: `POST /projects/{id}/extract` reads a stored `source_document`
and produces one or more `ExecutionEvent` rows via schema-constrained LLM extraction (never
free-form — see `docs/ARCHITECTURE.md` "AI Engineering Rules"). Needs an `execution_events` table
and a decision on which LLM provider/SDK to use (not yet made — flag for input, don't decide
silently). Image documents (`processable_now: false`) are correctly out of scope until OCR (P2).

## 21. Handoff Notes

- This is a from-scratch build. Repo `sri-ijan/Pragati` currently has only `.gitignore`, `LICENSE`,
  `README.md` — no code, no scaffolding.
- `plan.md` (the product/technical spec) is authoritative for anything product/technical; this
  `context.md` and the Master Engineering Prompt govern process only. See `plan.md` §0 priority order
  in §36 of the Master Prompt if anything conflicts.
- Do not simplify the matching pipeline (§10 above) or shrink the dataset target (~300 activities /
  150 events / 4 disciplines / 3 formats / 30+ ambiguous cases across all 7 edge-case categories) to
  save time. If time runs short, cut voice/OCR/real-P6-integration first — never the matching engine,
  review workflow, or audit trail (`plan.md` §25, §36).
- Before starting any task: read this file's §14 to see what teammates' AI sessions are doing.
  Update §14 immediately when you start or pause work, even mid-task.
