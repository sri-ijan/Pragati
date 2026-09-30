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
### 2026-09-21 — Slice 3 (AI extraction) implemented and verified

**Decision:** LLM provider = Anthropic Claude (`claude-sonnet-5` by default, overridable via
`ANTHROPIC_MODEL`), gated behind `ANTHROPIC_API_KEY`. No provider had been decided anywhere in
`plan.md`, `context.md`, `docs/ARCHITECTURE.md`, or `.env.example` before this slice — all three
explicitly said "not yet decided." Implemented behind an abstract `LLMProvider` interface
(`backend/services/llm_provider.py`) so this choice is swappable without touching
`extraction_service.py` or any route.
**Reason:** A concrete provider had to be picked to build something real per the Slice 3
instructions ("implement the clean provider boundary... tell me exactly which environment variable
I need to add"); Anthropic was the most natural default given the project's own tooling, and no
paid dependency was added without flagging it here and in the endpoint's own 503 error.
**Alternatives rejected:** OpenAI/Gemini/other providers — no signal either way in existing docs,
so not chosen over Anthropic without your input; a provider-neutral "bring your own adapter" system
with zero built-in implementation — rejected as not actually deliverable ("implement the... boundary
*and configuration*", not just the interface).
**Needs your input:** confirm this default is acceptable, or say which provider you'd rather use —
swapping is a new `LLMProvider` subclass plus a `get_llm_provider()` change, nothing else.

**Decision (flagged per your instruction to STOP and explain rather than silently resolve):**
`ExecutionEvent.event_date` is a **required** field on the locked schema. The extraction rules
correctly forbid ever inventing a date. For the given Hindi/English test example, the only date
reference is "kal" (tomorrow) — describing *future* work, not this event's own date — so a correct
LLM extraction returns `event_date: null`. Rather than (a) modifying the locked schema to make
`event_date` optional, or (b) failing extraction outright whenever no explicit date is stated, this
implementation falls back to **the source document's real upload timestamp** — genuine metadata, not
a guess — applied deterministically in `extraction_service.py`, never by the LLM itself (the model
only ever returns an explicit stated date or `null`). This matches standard "daily progress report"
convention (a field report is presumed to describe the day it was filed, absent contrary evidence),
but it IS a policy choice about how to satisfy a required field, not something the schema or the
extraction rules dictate outright — surfaced here rather than buried in code.
**Alternatives rejected:** Modifying `schemas.py`/`types.ts` to make `event_date` optional (avoided —
locked contract, and the instructions were explicit about not touching it without stopping first);
failing extraction whenever no explicit date exists (rejected — contradicts the instructions' own
verification example, which expects a successful `ExecutionEvent` for that exact input).
**Needs your input:** if you'd rather extraction fail cleanly (422) instead of using the upload-date
fallback whenever no explicit date is stated, say so — that's a one-line change in
`extraction_service.py`, not a contract change either way.

**Decision:** For every OTHER required field (`activity_description`, `discipline`, `action`,
`status`, `location`), no fallback is applied — if the LLM legitimately can't determine one, it
stays `null` and extraction fails with `422 EXTRACTION_INCOMPLETE`, listing exactly which fields.
**Reason:** Only `event_date` has a defensible, non-fabricated fallback available (real upload
metadata). There's no equivalent honest default for "what discipline is this" or "what location" —
guessing those would be exactly the kind of invented fact the instructions prohibit.

**Decision:** `discipline` may be inferred from unambiguous standard construction terminology (e.g.
"cable tray" → Electrical, "hydrotest"/"spool" → Piping) even when the word itself isn't in the
enum's vocabulary — encoded directly in the LLM system prompt, not a separate persisted terminology
dictionary/table.
**Reason:** This is recognizably "terminology normalization" from `plan.md`'s own pipeline diagram,
and it's what makes the given Hinglish test example (no literal word "Electrical" anywhere in it)
producible at all without guessing. A full persisted/editable terminology dictionary (the
`terminology` table already listed in `docs/API.md`'s minimum tables) was deliberately NOT built —
out of scope for "the first AI layer" as literally scoped; that table's real payoff is in Slice 4's
`terminology_score` matching component anyway.
**Alternatives rejected:** Building the `terminology` table now (deferred — not needed for a single
extraction call, adds scope not requested); refusing to infer discipline from terminology at all
(rejected — would make the given verification example fail, contradicting its expected outcome).

**Decision:** `quantity`/`unit` (both `Optional[float]`/`Optional[str]` on the locked schema) are
repurposed to carry a stated percentage — e.g. "60% done" → `quantity: 60, unit: "%"` — since no
dedicated progress-percentage field exists in the locked `ExecutionEvent` contract.
**Reason:** These two fields are the only generic optional numeric+unit carriers available without
touching the schema; percentage is numerically identical to any other stated quantity+unit pair.
**Alternatives rejected:** Dropping the percentage entirely (loses real, explicitly-stated
information for no reason); adding a `progress_percent` field to the locked schema (avoided per
instructions — this doesn't rise to "genuinely impossible," `quantity`/`unit` cover it adequately).

**Decision:** One `ExecutionEvent` produced per `POST .../extract` call (not multiple events split
out of one document), and extraction is not deduplicated — calling extract twice on the same
document creates two separate `execution_events` rows.
**Reason:** Matches the literal Slice 3 goal description (one field evidence → one canonical
event); splitting one document into several events, and/or de-duplicating repeat extraction, are
real future needs but add scope beyond "the first AI layer."
**Alternatives rejected:** none seriously considered — flagged as a known simplification, not
treated as a hard design decision, in case Slice 4 needs it changed.

**Decision:** Content extraction (`backend/services/document_text_extractor.py`) supports only
`.txt` (direct) and `.pdf` (text-layer only, via `pypdf`, no OCR). `.docx`/`.xlsx`/`.csv`/images all
return a clean `422 UNSUPPORTED_FOR_EXTRACTION` rather than a half-working parse.
**Reason:** `.txt` is what the actual field-update flow produces (`FieldUpdateForm.tsx` wraps typed
text as `.txt`); `.pdf` is explicitly named in `plan.md` as a DPR format. Real `.docx`/`.xlsx`
parsing and OCR are meaningfully more scope than "the first AI layer" asked for.
**Correction made along the way:** `GET /projects/{id}/documents`'s `processable_now` flag (Slice 2)
previously only excluded images. Since it's now known exactly what extraction supports, it's
derived from `document_text_extractor.EXTRACTABLE_EXTENSIONS` instead of a separately-maintained
image-only exclusion list — otherwise the flag would have kept claiming `.docx`/`.xlsx`/`.csv` were
processable when they aren't. This only changes what the flag reports, not Slice 2's upload/storage
mechanics, which are untouched.

**Verified:** 16 automated tests (`backend/tests/`, run via `pytest`, real SQLite persistence, a
`FakeLLMProvider` used only in tests per instructions — `get_llm_provider()` itself is never
mocked). Real end-to-end HTTP test against live Postgres in the build sandbox confirmed the
"missing API key" path: `POST /extract` with no `ANTHROPIC_API_KEY` set returned a clean `503
LLM_PROVIDER_NOT_CONFIGURED`, and nothing was persisted (`GET /events` stayed empty) — no fake
output. **Not verified:** an actual live Anthropic API call — no API key is available in the build
sandbox and none was fabricated; the extraction logic itself was verified deterministically instead
(see `backend/tests/test_extraction_service.py`).
### 2026-09-22 — LLM provider changed: Anthropic removed, Groq (primary) + Gemini (fallback) adopted

**Decision:** Replaced the Slice 3 Anthropic provider entirely with Groq as the primary provider and
Gemini as an automatic fallback. No Anthropic dependency, config, or code path remains anywhere in
the project. The `LLMProvider` abstraction from Slice 3 (`backend/services/llm_provider.py`) was
preserved and reused — `extraction_service.py` and `api/extraction.py` needed **zero changes**,
since they only ever depended on the generic `LLMProvider` interface and the exception types
(`LLMProviderNotConfigured`, `LLMExtractionError`), never on which concrete provider was behind it.
**Reason:** Explicit instruction — Anthropic's free tier was too limited for development use.
**Alternatives rejected:** N/A — explicit, unambiguous instruction.

**Decision:** Fallback triggers only on a new `LLMProviderUnavailable` exception (a subclass of
`LLMExtractionError`), raised by a provider only for rate limiting, quota exhaustion, connection
failure, or a temporary (5xx-class) server error. Any other failure from Groq — a malformed
response, an auth/permission/bad-request error, or the extracted JSON simply not parsing — is a
plain `LLMExtractionError` and does NOT trigger a Gemini call.
**Reason:** Explicit instruction: "Do NOT fallback merely because the extracted data is invalid.
Schema/validation problems should be handled separately." Interpreted narrowly and literally: only
the four availability-class reasons listed in the instructions (provider availability, rate limit,
quota exhaustion, temporary provider/API failure) trigger fallback; nothing else does.
**Alternatives rejected:** Falling back on any exception from Groq, including malformed/garbled
responses — rejected as broader than what was actually asked for, and would blur exactly the line
the instructions drew between "provider infrastructure failure" (retry-worthy) and "provider
responded but the response was bad" (not listed as retry-worthy).

**Decision:** A missing `GROQ_API_KEY` (Groq simply not configured) is treated as an availability
problem too — `_FallbackLLMProvider` goes straight to Gemini without erroring first, exactly as if
Groq had thrown `LLMProviderUnavailable`. `LLMProviderNotConfigured` is only raised when **neither**
`GROQ_API_KEY` nor `GEMINI_API_KEY` is set.
**Reason:** The whole point of having a fallback provider is resilience — including resilience to
the primary not being set up yet. This maximizes the chance extraction actually runs with whatever
single key the developer has configured, while still keeping "Groq first, Gemini only as fallback"
as the behavior whenever both are available.
**Alternatives rejected:** Requiring Groq to be configured before Gemini can ever be used — rejected
as needlessly brittle for a hackathon MVP where a developer may only have one key at a time.

**Decision:** Groq default model = `openai/gpt-oss-20b` (via `GROQ_MODEL`); Gemini default model =
`gemini-2.5-flash` (via `GEMINI_MODEL`). Structured output: Groq uses `response_format: {"type":
"json_schema", "strict": true}` (constrained decoding, chosen over Groq's legacy tool-calling
pattern since strict JSON-schema mode is Groq's current recommended structured-output mechanism);
Gemini uses `response_mime_type: "application/json"` + `response_schema` (JSON mode).
**Reason:** Strict mode on Groq is currently only supported on `openai/gpt-oss-20b`/
`openai/gpt-oss-120b` per Groq's own docs — picked the smaller/cheaper of the two as the default.
`gemini-2.5-flash` was checked against Google's current model-lifecycle page rather than assumed;
`gemini-2.0-flash` (an earlier, seemingly reasonable choice) was confirmed to have already been
shut down (June 2026), which is exactly the kind of stale-default mistake worth flagging — the
default was verified against current docs before being written down, not carried over from training
memory.
**Alternatives rejected:** Groq's best-effort (non-strict) JSON mode, available on more models —
rejected in favor of strict mode's stronger "never produces invalid JSON" guarantee, which matters
for a system that must never silently accept malformed extraction output.

**Decision:** `.env.example`'s LLM section now lists `GROQ_API_KEY`, `GROQ_MODEL`, `GEMINI_API_KEY`,
`GEMINI_MODEL` in place of the two Anthropic variables. `requirements.txt` swaps `anthropic==1.7.0`
for `groq==1.7.0` and `google-genai==2.24.0`. This forced two other pins upward for dependency
compatibility: `pydantic` 2.9.2 → 2.12.5 (google-genai requires >=2.12.5) and, in
`requirements-dev.txt`, `httpx` 0.27.2 → 0.28.1 (google-genai requires >=0.28.1). Neither bump
changed any application behavior — verified by the full test suite and a real end-to-end HTTP check
still passing after the bump.
**Reason:** Dependency resolution required it; picked the minimum versions that resolved cleanly
rather than jumping to the newest available, consistent with the project's existing "stable over
bleeding-edge" pattern (see the Next.js/React version decisions from the scaffolding phase).

**Verified:** all 26 backend tests pass (10 new/replaced tests specifically prove: Groq success
means Gemini is never called; a Groq availability failure triggers a Gemini call; both failing
raises the same `LLMExtractionError` `api/extraction.py` already handled before this change — no
new error-handling code needed there; a non-availability Groq failure does *not* trigger fallback;
API keys never appear in any exception message or provider object). Real end-to-end HTTP test
against live Postgres confirmed the "neither key configured" path still fails cleanly (503,
message now naming `GROQ_API_KEY`/`GEMINI_API_KEY`, nothing persisted). `npm run build` clean — the
frontend has zero provider-specific code and needed no changes. **Not verified:** an actual live
Groq or Gemini API call — no key for either is available in the build sandbox, none fabricated.
### 2026-09-23 — Slice 4 (matching engine) implemented and verified

**Decision (flagged per the established pattern — a real contract gap found before writing code,
not worked around silently):** `CONFIDENCE_WEIGHTS` in the locked `models/schemas.py` defines a
5-component formula (semantic/metadata/llm_rerank/temporal/**terminology**), but the locked
`MatchRecord` schema only has 4 score fields — there is no `terminology_score` field to store that
fifth component in. Resolution: `matching_service.py` still computes a terminology signal (token
overlap between the event's own description/action and each candidate's description) and folds it
into `final_confidence` using the exact locked formula — it just isn't exposed as its own numeric
field on the returned `MatchRecord`. It does surface as a `reason[]` string ("Shared terminology:
...") when it meaningfully contributes, partially preserving the explainability `docs/DESIGN.md`
wanted. Neither `schemas.py` nor `shared/types.ts` was touched.
**Reason:** Adding a `terminology_score` field would be the "genuinely impossible without a change"
case worth stopping for — but it isn't genuinely impossible, just less explainable. The formula can
still be computed exactly as specified without the field existing to store one component in
isolation.
**Alternatives rejected:** Adding `terminology_score` to the locked schema (avoided — not asked for,
and not truly necessary to implement the formula, just to expose one more number); dropping the
terminology component from the formula entirely (rejected — the locked `CONFIDENCE_WEIGHTS` says
0.10, silently using 0.0 would make `final_confidence` wrong).
**Needs your input:** if you want `terminology_score` broken out as its own field for the UI later,
that's a locked-contract change — say so and I'll stop and make the case explicitly, per instruction,
rather than adding it unprompted.

**Decision:** Embeddings for semantic retrieval always use Gemini specifically
(`gemini-embedding-001`, 768 dimensions) — there is no Groq/Gemini "fallback" for embeddings the way
there is for extraction/reranking, because Groq has no embeddings API at all.
**Reason:** A technical fact about Groq's product, not a design choice — nothing to pick between.
**Consequence worth knowing:** `POST /events/{id}/match` requires `GEMINI_API_KEY` even if you're
running extraction/reranking on Groq alone with no Gemini key configured. Documented in
`docs/API.md` and `.env.example`, not left as a silent surprise.

**Decision:** Hard filter (Stage 1) excludes candidates ONLY on discipline mismatch. Location/area
is scored (`metadata_score`), not hard-filtered.
**Reason:** `plan.md`'s pipeline description lists several possible hard-filter signals (discipline,
area, WBS, line number, tags, date, status), but the actual `ScheduleActivity` schema (Slice 1,
locked) has no `line_number`, `wbs`-as-a-comparable-field, or tag columns to filter on, and
area/location naming varies enough in free text that hard-excluding on it risks throwing away
correct matches over a naming mismatch (e.g. "Rack B" vs "RackB"). Discipline is the one signal
that's a clean, exact match on the same 4-value canonical enum on both sides.
**Alternatives rejected:** Hard-filtering on area/location text equality (rejected — too brittle);
inventing schedule-side `line_number`/tag fields to filter on (rejected — would mean touching the
locked `ScheduleActivity` schema for a feature the actual dataset/parser doesn't populate).

**Decision:** Embeddings are cached per (project_id, activity_id) in `activity_embeddings`
(pgvector), computed once on first use and reused on subsequent match calls — not recomputed every
time, and not invalidated if a schedule activity's description later changes (e.g. via a corrected
re-upload).
**Reason:** Avoids paying for/waiting on an embeddings call for the same activity on every single
match request across every event in a project; cache invalidation for schedule edits is a real gap,
flagged rather than silently accepted as "fine."
**Alternatives rejected:** Recomputing on every match call (correct but wasteful and slow at even
moderate schedule sizes); building real cache invalidation now (deferred — schedule activities
don't currently get edited after upload in this MVP, so the gap has no live consequence yet).

**Decision:** A fresh `POST /events/{id}/match` call **replaces** the previous batch of candidates
for that event (delete + insert), rather than keeping history of every match run.
**Reason:** `GET /events/{id}/candidates` is contracted as "the last computed" result, implying one
current answer, not a history; a full match-run audit trail is schedule-update/review territory
(Slice 5/6), not this slice's scope.
**Alternatives rejected:** Accumulating every match run's rows — rejected as unrequested scope and a
mismatch with "the last computed" wording in the original Slice 0 contract note.

**Decision:** `LLMProvider`'s interface was extended with a second method, `rerank_candidates`,
reusing the exact same Groq-primary/Gemini-fallback machinery from Slice 3 (`_FallbackLLMProvider`
refactored to a generic `_call_with_fallback` helper shared by both methods) rather than building a
separate reranking-specific provider abstraction.
**Reason:** Matches what `context.md`'s own "Next Recommended Task" note said before this slice
started: "Slice 4's LLM reranking will reuse the same LLMProvider boundary rather than inventing a
second one." Keeps the fallback policy (availability-only triggers) identical and enforced in one
place for both capabilities instead of two copies that could drift apart.

**Decision:** If LLM reranking fails entirely (both providers exhausted, or the only configured one
fails), matching proceeds with `llm_score = 0` for every candidate rather than aborting the whole
match or fabricating a score.
**Reason:** A missing LLM signal should pull `final_confidence` down (correctly reflected via the
`0.20 × llm_rerank_score` term going to zero), not block the other three real signals
(semantic/metadata/temporal) from producing a usable, honestly-lower-confidence result.
**Alternatives rejected:** Failing the whole `/match` call if reranking fails (rejected — throws away
real semantic/metadata/temporal signal that's still valid) — this is different from Slice 3's
"missing provider fails the whole request" because here reranking is one signal among several, not
the only source of the answer.

**Decision:** `Base.metadata.create_all()`'s pgvector `Vector` column type compiles fine on SQLite
(used for most test fixtures), but pgvector's actual `<=>` cosine-distance SQL operator does not
exist on SQLite. `embedding_repository.top_k_similar` (the one function that issues that query) is
tested against real Postgres+pgvector in `test_embedding_repository_pgvector.py`, which
**skips itself** if Postgres/the vector extension isn't reachable; every other Slice 4 test
(orchestration, scoring math, persistence) runs on SQLite via mocking/monkeypatching that one
function.
**Reason:** Keeps the bulk of the suite fast and portable (no Postgres required to run most tests)
while still having one real, unmocked proof that the actual pgvector query returns correct
nearest-neighbor ordering — verified in this build sandbox with real Postgres 16 + pgvector 0.6.0.

**Bug found and fixed during verification (real, not hypothetical):**
`match_repository.replace_matches` inserted rows using `match.event_id` (from the `MatchRecord`
object) instead of the function's own `event_id` parameter. In the real caller
(`api/matching.py`), these always agree, so it wasn't a live production bug — but it's a fragile
"two sources of truth that happen to match" design, and a test written to call `replace_matches`
with an event_id different from what was embedded in the `MatchRecord` immediately caught it
(0 rows found where 1 was expected). Fixed to use the parameter as the single source of truth.
Kept as a reminder, same as the Slice 1 dedup bug: exercising real behavior with a test catches
things a code read-through doesn't.

**Verified:** 53 backend tests pass total (27 new for Slice 4: pure scoring-function tests, mocked
orchestration tests, real-Postgres pgvector tests, embeddings-provider config tests, match
persistence tests). Real end-to-end HTTP verification against live Postgres+pgvector in the build
sandbox: (1) no keys configured → clean `503 EMBEDDINGS_PROVIDER_NOT_CONFIGURED`; (2) with
placeholder (invalid) Groq/Gemini keys set, `POST /events/{id}/match` correctly reached the real
Gemini embeddings API call and surfaced its failure as a clean `502 EMBEDDINGS_FAILED` — this also
revealed that this build sandbox's network egress does not allowlist
`generativelanguage.googleapis.com` (or presumably `api.groq.com`), so a genuine successful live
call could not be verified here even with a real key; that's a sandbox limitation, not a code issue,
and won't apply in your real environment. `npm run build` clean — new "Find schedule matches"
UI added to `FieldUpdateForm.tsx`, no approve/correct/reject actions built (that's Slice 5).
### 2026-09-24 — Resolved: terminology_score added to the locked MatchRecord contract (Option B)

**Decision:** The Slice 4 contract gap flagged earlier (`CONFIDENCE_WEIGHTS` includes a
`terminology` component with no corresponding field on the locked `MatchRecord`) is now resolved by
explicitly adding `terminology_score: float` (Python) / `terminology_score: number` (TypeScript) to
both canonical contracts — `backend/models/schemas.py` and `shared/types.ts` — per your explicit
instruction to proceed with Option B from the two-option analysis. This supersedes the earlier
"Option A" state (terminology folded into `final_confidence` only, surfaced solely via `reason[]`)
but does **not** invalidate that earlier decision entry, which stays as written per this file's
append-only convention — it documents the gap and the interim resolution accurately for that point
in time.
**Reason:** Explicit instruction, following the analysis both of us reviewed together.
**Files changed:** `backend/models/schemas.py`, `shared/types.ts` (the two locked contracts —
additive field only, no other field touched, no weights/thresholds changed), `backend/models/orm.py`
(`ActivityMatchORM` +`terminology_score` column), `backend/services/matching_service.py`
(`score_candidate` now passes `terminology_score` into the returned `MatchRecord`; docstrings
updated to stop describing the gap as open), `backend/repositories/match_repository.py`
(`replace_matches` persists it), `backend/api/matching.py` (`GET /events/{id}/candidates`
reconstructs it from the ORM row — `POST /events/{id}/match` needed no separate change, since it
returns whatever `matching_service.find_matches` already produces), `backend/tests/test_matching_service.py`,
`test_matching_orchestration.py`, `test_match_repository.py` (updated + three new assertions proving
propagation end to end: unit level in `score_candidate`, orchestration level in `find_matches`, and
persistence round-trip in the repository), `docs/API.md` (example JSON + gap note updated to a
resolution note). No changes to `frontend/` — the existing candidate card only ever destructured
`candidate_activity_id`/`final_confidence`/`decision`/`reason`, so the additive TS field required no
code change, only flows through automatically via the `@shared/types` re-export.

**Database migration:** This project uses `Base.metadata.create_all()` with no Alembic — that call
only creates tables that don't yet exist, it does not alter existing ones. Any Postgres instance
where `activity_matches` was already created (e.g. from running Slice 4 before this change) needs
one manual command:
```sql
ALTER TABLE activity_matches ADD COLUMN terminology_score DOUBLE PRECISION NOT NULL DEFAULT 0;
```
This was tested for real in the build sandbox against an `activity_matches` table that already had
rows in it from earlier Slice 4 verification — the command ran cleanly, existing rows were
backfilled with `0` (not deleted), and the app started and served requests against the altered
table without any further changes needed. A completely fresh database (table doesn't exist yet)
needs no manual step at all — `create_all()` creates the table with the new column from the start.
No migration framework was introduced, per instruction.

**Verified:** 56 backend tests pass (53 prior + 3 new: a unit-level assertion in
`test_matching_service.py` that `score_candidate`'s output carries the correct
`terminology_score`, an orchestration-level assertion in `test_matching_orchestration.py` that
`find_matches`' output has the field, and a persistence round-trip assertion in
`test_match_repository.py`). Real, non-mocked end-to-end proof: manually inserted a project /
document / event / `activity_matches` row (with `terminology_score: 0.42`) directly into the
migrated Postgres table, then called the real running API's `GET /events/{id}/candidates` — the
JSON response included `"terminology_score": 0.42` exactly, confirming the full path (DB column →
ORM → repository → API response model → JSON) works, not just the Python-level unit tests.
`npm run build` clean, no frontend changes were needed.

**Slice 5 was NOT started.** No review/approval endpoints, no schedule-write logic, no audit trail
work — confirmed by `git`-equivalent file diff: only the files listed above were touched.