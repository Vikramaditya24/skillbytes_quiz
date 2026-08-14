# Skillbytes Quiz Application

A WhatsApp-style quiz app (React + FastAPI + MongoDB) built for the Skillbytes
full-stack hiring assignment. Flow: **Login → Exam → Subject → Chapter → Quiz
→ Result**, plus an **Analytics Dashboard** covering the three required
analytics APIs (Learning Velocity Index, Fatigue Analysis, Question Difficulty).

## Quick start (Docker)

```bash
cp backend/.env.example backend/.env   # optional, defaults work out of the box
docker compose up --build
```

- Backend: http://localhost:8000 (docs at `/docs`)
- Frontend: http://localhost:5173
- MongoDB: localhost:27017

Then seed the database (one-time, from the host or by exec-ing into the
backend container):

```bash
docker compose exec backend python scripts/seed.py
```

## Quick start (local, no Docker)

Requires Python 3.11+, Node 20+, and a local MongoDB running on `27017`.

```bash
# backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python scripts/seed.py
uvicorn app.main:app --reload

# frontend (separate terminal)
cd frontend
npm install
npm run dev
```

## Running tests

```bash
cd backend
pytest
```

Tests use `mongomock-motor` (in-memory Mongo) so no real database is needed
to run the suite. They cover: dummy auth, quiz progression, server-enforced
no-revisit/no-duplicate-submit, scoring, event-document shape, all three
analytics formulas (pure unit tests with known expected outputs), and
behavioral analytics tests against deterministic fixtures (a synthetic
"perfect learner" ranks first in LVI, a declining-performance session trips
the fatigue flag, a slow/low-accuracy question ranks harder than a
fast/high-accuracy one).

> **Note on this submission's dev environment:** this implementation was
> developed in a sandboxed environment without outbound network access, so
> the test suite and `pip install` could not be executed here before
> submission. Everything has been written and reviewed for correctness, but
> please run `pytest` locally to confirm - see the self-review section below
> for what to watch for.

## Project structure

```
/backend
  /app
    /api            # routers: auth, catalog, quiz, analytics
    /services        # quiz progression + analytics orchestration
    /repositories     # Mongo access layer, one per collection
    /schemas          # Pydantic request/response models
    /core             # settings, db client, index creation
    /aggregations     # raw Mongo pipelines + pure scoring formulas
  /scripts/seed.py     # deterministic seed data generator
  /tests
/frontend
  /src/pages           # Login, Exams, Subjects, Chapters, Quiz, Result, Dashboard
  /src/api/client.js    # thin fetch wrapper
docker-compose.yml
```

Router → Service → Repository, one direction of dependency. Trivial CRUD
(list exams/subjects/chapters) goes straight from router to repository - no
service-layer ceremony for a one-line query. Service layer exists only where
there's real logic: quiz progression/scoring and analytics assembly.

## Database design

Everything is reference-based (ObjectId links), not embedded.
`question_attempts` is a high-write, high-cardinality event stream (50 users
× multiple sessions × up to 15 questions each); embedding it into
`quiz_sessions` or `users` would force unbounded array growth and rule out
the aggregation patterns analytics needs.

`exam_id` / `subject_id` / `chapter_id` are the one deliberate denormalization
- copied as scalar fields onto `questions` and `question_attempts` so
analytics pipelines can `$match` by ancestry without a `$lookup` chain
(attempt → question → chapter → subject → exam). This is safe because
ancestry is immutable: a question never moves chapters.

**Collections:** `users`, `exams`, `subjects`, `chapters`, `questions`,
`quiz_sessions` (mutable progression state), `question_attempts` (canonical,
immutable analytics event stream - the single source of truth for all three
analytics APIs; the analytics service only ever reads from it, never writes).

**Indexes** (see `app/core/db.py` - each has a documented reason, no
speculative indexes on small lookup tables like `exams`/`subjects`):

| Collection | Index | Reason |
|---|---|---|
| `questions` | `{chapter_id: 1}` | Sampling a chapter's question pool at session start |
| `quiz_sessions` | `{user_id: 1, status: 1}` | Resuming/checking in-progress sessions |
| `question_attempts` | `{session_id: 1, question_id: 1}` unique | The real DB-level backstop against duplicate submits/revisits |
| `question_attempts` | `{user_id: 1, session_id: 1, question_sequence_number: 1}` | LVI (per-user) and Fatigue (per-session windowing) both `$match` on this first |
| `question_attempts` | `{question_id: 1}` | Question Difficulty groups by question |

## No-revisit / server-enforced progression

The client never decides which question comes next. `quiz_sessions.current_index`
is the server's pointer into the session's fixed `question_ids` array. Submitting
an answer for any question other than the one at `current_index` is rejected
(HTTP 409). Advancing `current_index` is done with an atomic
`find_one_and_update` conditioned on the *expected* current index, which also
closes the race condition where a client double-submits the same answer.
The unique `(session_id, question_id)` index is a second, independent backstop
at the database layer.

## Analytics methodology

All three read only from `question_attempts`; grouping/math is done in Mongo
aggregation pipelines (`app/aggregations/pipelines.py`), and the small grouped
result set is turned into scores by pure, isolated formula functions
(`app/aggregations/formulas.py`) that are unit-tested directly.

**Accuracy** = correct / total × 100.

**Speed score** (0-100): relative position within the *observed* response-time
range for that cohort - fastest observed time → 100, slowest → 0, linear
in between. If every attempt took the same time (or n=1), returns a neutral
50 rather than dividing by zero.

**Consistency score** = `100 / (1 + coefficient_of_variation)` where CV =
stddev / mean of response time. Lower variance → higher score. Undefined for
n<2 or mean=0 - returns `null` with a `low_sample: true` flag rather than
fabricating a number; the dashboard renders "insufficient data" for these.
n≥2 but n<5 is still scored but still flagged, since 2-4 points is weak
evidence.

**Learning Velocity Index** = 50% accuracy + 30% speed + 20% consistency.
Weights are named constants in `app/core/config.py`, not buried magic numbers.
Accuracy dominates because the metric is explicitly "Learning *Velocity*" -
speed and consistency are meant to be secondary/tie-breaking signals, not able
to outrank a highly-accurate-but-average-speed learner. When consistency is
null (low sample), the composite uses a neutral 50 for that component only,
and the row is still visually flagged, not hidden.

**Fatigue Analysis**: attempts grouped into fixed windows of `question_sequence_number`
(default size 5, configurable via `FATIGUE_WINDOW_SIZE`). Each window's
accuracy and average response time are compared against that *session's own*
first window. `fatigue_flag` is set only when accuracy drops by more than 5
percentage points **and** response time rises by more than 10% versus
baseline - both signals required, so naturally-harder-later-questions alone
don't get mislabeled as fatigue. This is explicitly a descriptive heuristic,
not a scientific or causal claim, and the API response says so directly.

**Question Difficulty Score** = 70% inverted accuracy (100 - accuracy%) + 30%
relative response-time difficulty, where response time is normalized *within
the question's own chapter* (so a naturally slower chapter, e.g. a
reading-comprehension chapter, doesn't make every one of its questions look
"hard" relative to a quick-recall chapter). Deliberately not `1 - accuracy`
alone - response time materially moves the ranking.

## Assumptions

1. **"Four analytics APIs" wording.** The assignment PDF states "the
   following four analytics APIs are the primary evaluation criteria" but
   then numbers and describes exactly **three** (Learning Velocity Index,
   Fatigue Analysis, Question Difficulty Index). No fourth metric is named
   anywhere in the document. Treated as a wording error in the source, not an
   unstated requirement - implementing a fourth, ungrounded metric (e.g. an
   invented "engagement score") to satisfy the literal word count would be
   scope creep with no spec to validate it against.
2. **Exam/Subject/Chapter cardinality.** Strict tree hierarchy: one exam per
   subject, one subject per chapter, one chapter per question. 10 subjects
   are split unevenly across 3 exams (3/3/4) since 10 doesn't divide evenly
   by 3.
3. **Quiz session size.** A session samples up to 15 questions from the
   parent chapter's pool (configurable via `QUIZ_SESSION_SIZE`), randomized
   per session. Chosen because the Fatigue spec's own example ("Questions
   1-5, 6-10, 11-15") implies 15-question sessions, and re-samplable sessions
   give the analytics enough volume across only 50 seeded users.
4. **Timestamp authority.** Both `shown_at` and `answered_at` are stamped
   server-side (when the question is served / when the answer is received),
   not trusted from the client - consistent with the spec's "don't rely
   solely on frontend state" instruction. Trade-off: `response_duration_ms`
   includes network round-trip latency; documented rather than hidden.
5. **`quiz_id` vs. `session_id`.** The spec's event-tracking list names
   `Quiz ID`; internally this is the quiz session id (`quiz_sessions._id`),
   since a "quiz" in this app is a stateful session (sampled question order +
   progression pointer), not a static entity. `question_attempts.session_id`
   is what's meant by the spec's `Quiz ID`.
6. **Auth.** Dummy login only, per the spec - selecting a predefined user
   returns their id as a `session_token`. No JWT, no password. Intentionally
   minimal.

## What was deliberately left out

Per the assignment's own guidance ("we are not evaluating how quickly you
can scaffold CRUD") and the 4-day scope: no Redis/Kafka/microservices/CQRS/
background workers, no production auth, no z-score/winsorization in the
analytics (an earlier draft had this; removed as unnecessary complexity for
formulas that need to stay explainable to a reviewer in one read), no
speculative indexes on collections with ≤10 documents.

## Self-review notes / known risks

Written and reviewed carefully, but **not executed** in this environment
(no network access to install dependencies) - please verify these when
running locally:

- `mongomock-motor` (used for the test suite) has partial aggregation
  support. `$sample` (used by `catalog_repo.sample_questions` for picking a
  chapter's quiz questions) and `$stdDevPop`/`$floor` (used by the analytics
  pipelines) may behave differently under mongomock than a real MongoDB.
  The quiz-progression tests were written to construct sessions directly
  (bypassing `$sample`) specifically to avoid that risk; the analytics
  aggregation tests do exercise the real pipelines against mongomock and are
  the most likely place to need a small fix if mongomock's operator support
  falls short - if so, they're straightforward to also run against a real
  local MongoDB instead.
- The seed script (`scripts/seed.py`) has not been run end-to-end here for
  the same reason. Logic was written carefully (deterministic RNG seed,
  question pool sizing that guarantees ≥15 questions per chapter, six named
  behavioral archetypes cycled across the 50 users) but should be run and
  its output spot-checked before recording the Loom walkthrough.
- Frontend has not been `npm install`'d/built in this environment; component
  structure and API contract match the backend schemas but haven't been
  visually verified.

## Loom walkthrough checklist (for your recording)

- [ ] Project structure walkthrough (this README's structure section)
- [ ] Database design + why (denormalized ancestry fields, reference vs
      embedding decision, index table)
- [ ] Analytics implementation: pipelines.py (Mongo side) vs formulas.py
      (pure Python scoring), and the dashboard's "How is this calculated?"
      panels
- [ ] Assumptions section (especially #1 - the "four vs three" discrepancy)
