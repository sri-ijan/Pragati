# SetuAI — Decisions Log

Append-only. Add a new entry per decision; never rewrite history. Cheap to touch — add entries as
they happen, not just at phase boundaries.

---

### 2026-09-15 — Adopted `plan.md` as authoritative product/technical spec

**Decision:** `plan.md` (SIH PS 122 — AI-Powered Field-to-Schedule Reconciliation) governs all
product and technical substance. The Master Engineering Prompt governs process/workflow only.
**Reason:** Two-document split (Master Prompt §0) — avoids re-deriving smaller/simpler versions of
the spec during implementation sessions.
**Alternatives rejected:** Treating the Master Engineering Prompt as also authoritative for product
scope (rejected — it explicitly defers to `plan.md` on substance).

---

### 2026-09-15 — Repository name stays "Pragati"; product name is "SetuAI"

**Decision:** Keep the existing GitHub repo name (`sri-ijan/Pragati`) rather than renaming it to
match the product name used in `plan.md`/pitch materials ("SetuAI").
**Reason:** Repo already existed with commit history before the product name was finalized;
renaming is low-cost and can happen anytime without blocking work.
**Alternatives rejected:** Renaming the repo now, or creating a new repo named `setuai`.

---

### 2026-09-15 — Planning/context phase completed before any implementation

**Decision:** `context.md` and all six `docs/` files created from `plan.md` before any code is
written, per Master Engineering Prompt §39 (First Action).
**Reason:** Repo was completely empty (only `.gitignore`, `LICENSE`, `README.md`); no prior
`context.md` existed for any teammate's AI session to build on.
**Alternatives rejected:** Starting directly on Slice 1 implementation without first establishing
shared context — rejected per §2 ("Plan Before Code") and §7B (Slice 0 must be blocking).

---

<!-- Add new entries above this line, most recent first is fine as long as each entry is dated. -->
### 2026-09-16 — Slice 0 closed: shared contracts locked

**Decision:** Canonical types (`ExecutionEvent`, `ScheduleActivity`, `MatchRecord`, `AuditLogEntry`,
`Project`) implemented as real typed files — `shared/types.ts` (frontend) and
`backend/models/schemas.py` (backend) — instead of staying prose-only in `plan.md`/`context.md`.
Both are hand-kept in sync; no code generation step for now (small enough to do by hand at MVP scale).
**Reason:** Master Prompt §14 — a type defined once and imported by every track is what prevents
integration breakage at hour 30; prose alone doesn't give the compiler/linter anything to check.
**Alternatives rejected:** Codegen from a single OpenAPI/JSON-Schema source (more setup than the
hackathon timeline justifies for ~6 types).

**Decision:** No auth for the MVP; all API endpoints open; `reviewer` is a plain typed-name string
field on write requests, not a session identity.
**Reason:** `plan.md` §1 explicitly lists enterprise-grade identity/security as a non-goal.
**Alternatives rejected:** A minimal login/session layer — rejected as scope the PS doesn't need.

**Decision:** Uploaded files stored on local disk under `data/uploads/{project_id}/{source_document_id}/`
for the MVP.
**Reason:** Object storage adds hackathon-timeline infra risk for zero demo benefit; `plan.md` §5
explicitly says avoid spending time on complex infrastructure.
**Alternatives rejected:** S3-compatible object storage now — deferred to a "production would..." note.

**Decision:** Standard error envelope `{ "error": { "code", "message", "details" } }` across all
endpoints.
**Reason:** One shape for the frontend to switch on, instead of ad hoc per-endpoint error bodies.
**Alternatives rejected:** Per-endpoint bespoke error shapes.
### 2026-09-18 — Solo development mode (not parallelized)

**Decision:** Development is proceeding solo, sequentially, one task at a time — the Master
Engineering Prompt's 6-person parallel-track model (§7) is not being applied right now.
**Reason:** Explicit instruction from the developer actually building this.
**Alternatives rejected:** N/A — this supersedes the *process* assumption only; it does not change
any product/technical contract (`plan.md`, `shared/types.ts`, `backend/models/schemas.py`,
`docs/API.md` all unchanged).

### 2026-09-18 — Slice 1 scaffolding: stack choices and verification

**Decision:** Backend — FastAPI app with `api/`, `config/`, `models/`, `services/` packages;
Postgres via SQLAlchemy with a lazily-created engine (backend starts fine even if Postgres isn't
running yet); only a `/health` and `/health/db` route exist, no feature routers.
**Decision:** Frontend — Next.js 14 (App Router) + React 18 + TypeScript 5 + Tailwind 3, pinned to
stable majors rather than the newest available (Next 16 / React 19 / Tailwind 4 / TS 7 were live on
npm at scaffolding time) for configuration reliability. Pinned `next@14.2.35` specifically (not
`14.2.0`) after `npm install` flagged a known CVE in `14.2.0`.
**Decision:** `frontend/types/shared.ts` re-exports `shared/types.ts` via a `@shared/*` path alias
in `tsconfig.json`, instead of copying/duplicating the canonical types into the frontend package.
**Reason:** Keep the scaffolding minimal, avoid unfamiliar bleeding-edge config surface (e.g.
Tailwind v4's CSS-based config, an RC-stage TypeScript major) this early, and never let a second
copy of the canonical contracts exist.
**Verified:** `backend` — `pip install`, `uvicorn main:app` starts, `GET /health` → 200, `GET
/health/db` → 200 with `connected:false` (Postgres not running in the sandbox) without crashing the
app, `/docs` (Swagger) loads. `frontend` — `npm install`, `npm run build` succeeds including type
-checking (confirms the `@shared/types` alias resolves), `npm run dev` serves the placeholder page
at `/`.
**Open for the developer's input:** whether to accept the Next.js Image-Optimization CVE
(`GHSA-2xp9-vwfh-vxw4`, unrelated to any feature we use yet) by staying on patched 14.2.x, or jump
straight to Next 16 now — flagged, not decided unilaterally.
### 2026-09-19 — Slice 1 (schedule upload) implemented and verified

**Decision:** Table creation via `Base.metadata.create_all()` at FastAPI startup (in a `lifespan`
handler), not Alembic migrations, for `projects` and `schedule_activities`.
**Reason:** Two tables, single-developer MVP, hackathon timeline — Alembic's setup cost isn't
justified yet. Revisit if schema churn across the team gets painful once matching/review tables
land (Slice 4/5).
**Alternatives rejected:** Alembic from the start.

**Decision:** ORM models live in `backend/models/orm.py`, a new file separate from the locked
`backend/models/schemas.py`.
**Reason:** `schemas.py` is the Slice 0 canonical API/domain contract (Pydantic) and was explicitly
not to be touched; persistence-layer concerns (SQLAlchemy columns, FKs, autoincrement PKs) are a
different layer and don't belong in the same file.
**Alternatives rejected:** Adding `Config` classes to make `schemas.py` double as ORM models
(rejected — conflates two concerns and risks contract drift).

**Decision:** Schedule upload dedup — re-uploading a file skips any `activity_id` already stored
for that project, rather than erroring the whole request or overwriting silently.
**Reason:** Demo-safety: a planner re-uploading the same/updated schedule file shouldn't crash or
silently double-count activities. Overwrite-on-conflict is a reasonable alternative but was not
built — flagged here in case Slice 5 (progress updates) needs it.
**Alternatives rejected:** Reject the whole upload on any duplicate ID; silently overwrite existing
rows on conflict.

**Bug found + fixed during verification:** `schedule_repository.bulk_insert_activities` built its
existing-ID set from `db.execute(select(ScheduleActivityORM.activity_id)...).scalars()` and then
iterated `row.activity_id` — but `.scalars()` on a single-column select already yields the raw
string values, not row objects, so this raised `AttributeError` on every re-upload. Fixed to
`set(db.execute(...).scalars())`. Caught by an actual re-upload test against real Postgres, not
just a code read-through — worth remembering as a reason to keep running real end-to-end checks
rather than trusting review alone.
### 2026-09-20 — Slice 2 (field document intake) implemented and verified

**Decision:** Added `GET /projects/{id}/documents` — not in the original Slice 0 endpoint list.
**Reason:** Slice 2 needed some way to see what had been uploaded, same gap `GET
/projects/{id}/schedule` filled for Slice 1 (that one *was* contracted; this one wasn't). Flagged
per your instruction rather than added silently.
**Alternatives rejected:** Leaving document visibility to direct DB inspection only — rejected,
makes the frontend list (and any future debugging) unnecessarily painful for zero benefit.

**Decision:** Project creation moved out of `ScheduleUploadForm` into a standalone
`ProjectCreateForm`, with `app/page.tsx` now owning `projectId` state.
**Reason:** Slice 2's field-update form needs the same `projectId` Slice 1's schedule form uses;
duplicating project creation in two components would create two independent projects instead of
one shared one.
**Alternatives rejected:** Giving `FieldUpdateForm` its own independent project-creation flow
(rejected — defeats the point of one project having both a schedule and field updates).

**Decision:** A typed text field update is wrapped client-side into a `.txt` `File` and sent
through the same `documents/upload` endpoint, rather than adding a separate "raw text" request
shape.
**Reason:** `docs/API.md` only contracted a multipart file upload for this endpoint; reusing it
avoids inventing a second document-intake path for what's ultimately the same downstream record.
**Alternatives rejected:** A new `POST .../documents/text` endpoint accepting `{ text: string }`
directly (would require touching the locked contract for a purely client-side convenience).

**Decision:** Image uploads (`.jpg/.png`) are accepted by the endpoint but returned with
`processable_now: false`, since OCR extraction doesn't exist (P2 per `plan.md`).
**Reason:** Matches `docs/API.md`'s already-stated "optionally a simple image" note without
pretending the system can currently do anything with it — avoids a §31 "no fake implementation"
violation where an image looks accepted-and-handled but silently goes nowhere.
**Alternatives rejected:** Rejecting image uploads outright (rejected — contract already allows
them); silently accepting with no signal that they won't be processed (rejected — misleading).

**Decision:** Upload size limit and storage directory centralized into `config/settings.py`
(`max_upload_bytes`, `uploads_dir`); `api/schedule.py` refactored to use the shared setting instead
of its own local `MAX_UPLOAD_BYTES` constant.
**Reason:** Two upload endpoints now exist with the same documented 10 MB limit — one source of
truth avoids them silently drifting apart later.
