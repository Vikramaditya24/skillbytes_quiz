# Skillbytes Quiz Application

A quiz platform (React + FastAPI + MongoDB) built for the Skillbytes full-stack
hiring assignment. Flow: **Login -> My Progress -> Exam -> Subject -> Chapter ->
Quiz -> Result**, plus a separate **Cohort Analytics** section covering the
three required analytics APIs (Learning Velocity Index, Fatigue Analysis,
Question Difficulty Index).

## Setup instructions

### Option A - Docker

```bash
cp backend/.env.example backend/.env   # optional, defaults work out of the box
docker compose up --build
```

- Backend: http://localhost:8000 (interactive docs at /docs)
- Frontend: http://localhost:5173
- MongoDB: localhost:27017

Then seed the database (one-time; re-run any time you want a fresh deterministic dataset):

```bash
docker compose exec backend python scripts/seed.py
```

### Option B - Local, no Docker

Requires Python 3.11+, Node 20+, and a MongoDB instance reachable at
mongodb://localhost:27017 (the quickest way to get one without installing
MongoDB natively is `docker run -d --name skillbytes-mongo -p 27017:27017 mongo:7`).

```bash
# backend
cd backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python scripts/seed.py
uvicorn app.main:app --reload

# frontend (separate terminal)
cd frontend
npm install
npm run dev
```

The seed script prints a "Demo users" list at the end - one user per
behavioral pattern (high-accuracy-fast, high-accuracy-slow, improving,
declining, inconsistent, low-accuracy) with amplified signal, specifically
for demoing distinct analytics during the Loom walkthrough. Log in as any of
them from the login screen.

## Testing instructions

```bash
cd backend
pytest
```

Tests use mongomock-motor (in-memory Mongo), so no real database is needed
to run the suite - except TestSeedScriptIdentitiesAndCounts in
test_seed_content.py, which imports scripts/seed.py and therefore needs
motor importable (it does not touch a database, but seed.py imports motor
at module scope). If motor isn't installed, that one test class is skipped
via pytest.importorskip, not silently passed.

Test coverage:
- test_formulas.py - pure unit tests for every analytics formula (accuracy,
  speed, consistency, LVI, difficulty, fatigue deltas/flag) against known
  inputs/outputs, including edge cases (n=1, equal min/max, zero mean).
- test_quiz_progression.py - question ordering, scoring, no-revisit
  enforcement, duplicate-submit rejection, session completion, session
  ownership (a user cannot view/answer/get-results for another user's
  session), and a regression test for the shown_at idempotency fix
  (repeated current-question calls must not reset the timestamp).
- test_analytics_aggregation.py - behavioral tests against deterministic
  fixtures with known expected outcomes (a synthetic "perfect learner" ranks
  #1 in LVI, a declining-performance session trips fatigue_flag, a
  slow/inaccurate question outranks a fast/accurate one in difficulty).
- test_my_progress.py - confirms the personal-progress endpoint is
  correctly scoped per user (two users' attempts never mix) and correctly
  reports "no data yet" for a fresh user.
- test_auth_and_events.py - dummy login, event-document field completeness,
  and confirms the internal _archetype seed field never appears in any API
  response.
- test_seed_content.py - question-bank correctness (exactly 4 options,
  exactly 1 correct answer, no duplicate question text within a chapter, no
  leftover placeholder text, deterministic given the same seed) and seed
  script identity/archetype checks (realistic "First Last" names, no
  "User14"-style names, unique emails, all 6 archetypes represented and
  balanced, archetype assignment decoupled from name assignment).

What was actually run vs. not, and why, is in the "Status of this
submission" section at the bottom of this README - please read it before
assuming the whole suite has been executed end-to-end.

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
  /scripts
    seed.py            # deterministic seed data generator
    question_bank.py    # deterministic, template-based MCQ content generator
  /tests
/frontend
  /src/pages           # Login, MyProgress, Exams, Subjects, Chapters, Quiz, Result, CohortAnalytics
  /src/api/client.js    # thin fetch wrapper
docker-compose.yml
```

Router -> Service -> Repository, one direction of dependency. Trivial CRUD
(list exams/subjects/chapters) goes straight from router to repository - no
service-layer ceremony for a one-line query. Service layer exists only where
there's real logic: quiz progression/scoring and analytics assembly.

## Product model: My Progress vs. Cohort Analytics

Login is dummy (per the assignment spec), but it still has a real, visible
consequence: after logging in, a learner lands on My Progress - their own
Learning Velocity Index, accuracy, recent quiz history, and (if they have a
completed session) their own fatigue trend. This data is strictly scoped to
the logged-in user; another learner's numbers never appear here.

Cohort Analytics is a separate, clearly-labeled section holding the existing
ranked/comparative views (LVI leaderboard across all learners, fatigue
browser across all sessions, question difficulty ranking across all
questions). This is intentionally not scoped to one user - the metrics are
inherently comparative ("rank users by LVI" requires seeing all users), and
the assignment's analytics APIs are specified as cross-learner by
definition. No admin role or extra auth was introduced for this: any
logged-in user can view Cohort Analytics, but the UI makes unmistakably
clear which section is "you" and which is "everyone."

Both sections reuse the exact same formulas and Mongo pipelines - "My
Progress" calls the same learning_velocity() / fatigue_analysis() service
methods as Cohort Analytics, with an optional $match on user_id prepended to
the pipeline (see app/aggregations/pipelines.py). This is one implementation
with two scopes, not a duplicated one.

## Session ownership

Every session-scoped endpoint (current-question, answer, result) requires
the caller's user_id and checks it against the session's actual owner
(quiz_sessions.user_id), raising OwnershipError -> HTTP 403 on mismatch
(app/services/quiz_service.py). Given dummy auth, "being logged in" is
knowing your own user_id - so this is the correct and sufficient enforcement
boundary for this assignment's auth model without introducing JWTs or a
permissions system. A learner cannot view or interfere with another
learner's in-progress quiz by guessing or incrementing a session id.

## Database design

Everything is reference-based (ObjectId links), not embedded.
question_attempts is a high-write, high-cardinality event stream (50 users
x several sessions x up to 15 questions each); embedding it into
quiz_sessions or users would force unbounded array growth and rule out the
aggregation patterns analytics needs.

exam_id / subject_id / chapter_id are the one deliberate denormalization -
copied as scalar fields onto questions and question_attempts so analytics
pipelines can $match by ancestry without a $lookup chain (attempt ->
question -> chapter -> subject -> exam). This is safe because ancestry is
immutable: a question never moves chapters.

Collections: users (includes an internal-only _archetype field used solely
by the seed script - never returned by any API, see
test_auth_and_events.py::TestNoArchetypeLeak), exams, subjects, chapters,
questions, quiz_sessions (mutable progression state), question_attempts
(canonical, immutable analytics event stream - the single source of truth
for all three analytics APIs; the analytics service only ever reads from
it, never writes).

Indexes (see app/core/db.py - each has a documented reason, no speculative
indexes on small lookup tables like exams/subjects):

| Collection | Index | Reason |
|---|---|---|
| questions | {chapter_id: 1} | Sampling a chapter's question pool at session start |
| quiz_sessions | {user_id: 1, status: 1} | Resuming/checking in-progress sessions; My Progress's recent-sessions lookup |
| question_attempts | {session_id: 1, question_id: 1} unique | The real DB-level backstop against duplicate submits/revisits |
| question_attempts | {user_id: 1, session_id: 1, question_sequence_number: 1} | LVI (per-user) and Fatigue (per-session windowing) both $match on this first |
| question_attempts | {question_id: 1} | Question Difficulty groups by question |

## No-revisit / server-enforced progression

The client never decides which question comes next. quiz_sessions.current_index
is the server's pointer into the session's fixed question_ids array.
Submitting an answer for any question other than the one at current_index
is rejected (HTTP 409). Advancing current_index is done with an atomic
find_one_and_update conditioned on the expected current index, which also
closes the race condition where a client double-submits the same answer.
The unique (session_id, question_id) index is a second, independent
backstop at the database layer.

### shown_at idempotency fix

An earlier version of this codebase unconditionally overwrote
shown_at_by_index.{idx} on every call to current-question, meaning a page
refresh or a retried request would silently reset the clock that
response_duration_ms is measured against. This is now fixed: the update is
conditioned on {"$exists": False}, so shown_at is stamped once, on the first
time a given question is served, and never again - regardless of how many
times the endpoint is subsequently called for the same question. See
app/services/quiz_service.py::get_current_question and the regression tests
in test_quiz_progression.py::TestShownAtIdempotency.

## Analytics methodology

All three read only from question_attempts; grouping/math is done in Mongo
aggregation pipelines (app/aggregations/pipelines.py), and the small grouped
result set is turned into scores by pure, isolated formula functions
(app/aggregations/formulas.py) that are unit-tested directly. Formulas are
unchanged from the original implementation - no z-scoring, winsorization, or
other statistical complexity was reintroduced during the rebuild, per
explicit instruction.

Accuracy = correct / total x 100.

Speed score (0-100): relative position within the observed response-time
range for that cohort - fastest observed time -> 100, slowest -> 0, linear
in between. If every attempt took the same time (or n=1), returns a neutral
50 rather than dividing by zero.

Consistency score = 100 / (1 + coefficient_of_variation) where CV =
stddev / mean of response time. Lower variance -> higher score. Undefined
for n<2 or mean=0 - returns null with a low_sample: true flag rather than
fabricating a number; the UI renders "insufficient data" for these. n>=2 but
n<5 is still scored but still flagged, since 2-4 points is weak evidence.

Learning Velocity Index = 50% accuracy + 30% speed + 20% consistency.
Weights are named constants in app/core/config.py, not buried magic numbers.
Accuracy dominates because the metric is explicitly "Learning Velocity" -
speed and consistency are meant to be secondary/tie-breaking signals, not
able to outrank a highly-accurate-but-average-speed learner. When
consistency is null (low sample), the composite uses a neutral 50 for that
component only, and the row is still visually flagged, not hidden.

Fatigue Analysis: attempts grouped into fixed windows of
question_sequence_number (default size 5, configurable via
FATIGUE_WINDOW_SIZE, matching the spec's own "Questions 1-5, 6-10, 11-15"
example). Each window's accuracy and average response time are compared
against that session's own first window. fatigue_flag is set only when
accuracy drops by more than 5 percentage points AND response time rises by
more than 10% versus baseline - both signals required, so
naturally-harder-later-questions alone don't get mislabeled as fatigue.
This is explicitly a descriptive heuristic, not a scientific or causal
claim, and the API response says so directly (disclaimer field).

Question Difficulty Score = 70% inverted accuracy (100 - accuracy%) + 30%
relative response-time difficulty, where response time is normalized within
the question's own chapter (so a naturally slower chapter, e.g. a
reading-comprehension chapter, doesn't make every one of its questions look
"hard" relative to a quick-recall chapter). Deliberately not 1 - accuracy
alone - response time materially moves the ranking.

Every metric has a plain-language "How is this calculated?" explanation
inline in the UI (My Progress and Cohort Analytics both), so an evaluator
can understand each number without reading source code.

## Seed data

scripts/seed.py is fully deterministic (fixed RNG_SEED = 42 - reruns
produce identical data) and populates:

- 50 users with realistic "First Last" names and
  firstname.lastname@learnhub.test emails, generated independently of their
  behavioral archetype (no naming pattern reveals which archetype a user
  has - see
  test_seed_content.py::test_archetype_assignment_independent_of_name_order).
  Archetype is stored as an internal-only _archetype field and never
  surfaced through any API.
- 3 exams, 10 subjects (3/3/4 split), 30 chapters, 500 questions. Questions
  are generated by scripts/question_bank.py - a deterministic,
  template-based content system, not placeholder text and not an LLM call.
  Math/science subjects (Algebra, Geometry, Mechanics, Thermodynamics)
  compute a genuine numeric answer from randomized-but-deterministic
  parameters, with plausible near-miss distractors (off-by-one-step
  arithmetic errors, common formula confusions - e.g. area vs. perimeter).
  Fact-based subjects (Organic Chemistry, Cell Biology, Modern History,
  Political Science, Grammar, Vocabulary) draw from curated fact banks
  cycled through two phrasing variants each, sized so that no chapter (~17
  questions) ever repeats a question - verified by
  test_seed_content.py::TestQuestionBankContent across multiple RNG seeds.
- Six behavioral archetypes (high_accuracy_fast, high_accuracy_slow,
  improving, declining, inconsistent, low_accuracy) cycled across the 50
  users, each with distinct accuracy/response-time/trend parameters. The
  first user assigned to each archetype is a "hero" user - 5 completed
  sessions instead of 2-3, and an amplified version of that archetype's
  signal - specifically so that a single learner's own My Progress charts
  demonstrate the pattern clearly, not just the cohort-wide ranking. The
  script prints these six users' names/emails at the end of its run.

## Assumptions

1. "Four analytics APIs" wording. The assignment PDF states "the following
   four analytics APIs are the primary evaluation criteria" but then
   numbers and describes exactly three (Learning Velocity Index, Fatigue
   Analysis, Question Difficulty Index). No fourth metric is named anywhere
   in the document. Treated as a wording error in the source, not an
   unstated requirement.
2. Exam/Subject/Chapter cardinality. Strict tree hierarchy: one exam per
   subject, one subject per chapter, one chapter per question. 10 subjects
   are split unevenly across 3 exams (3/3/4) since 10 doesn't divide evenly
   by 3.
3. Quiz session size. A session samples up to 15 questions from the parent
   chapter's pool (configurable via QUIZ_SESSION_SIZE), randomized per
   session. Chosen because the Fatigue spec's own example implies
   15-question sessions, and re-samplable sessions give the analytics
   enough volume across only 50 seeded users.
4. Timestamp authority. Both shown_at and answered_at are stamped
   server-side, not trusted from the client - consistent with the spec's
   "don't rely solely on frontend state" instruction. Trade-off:
   response_duration_ms includes network round-trip latency; documented
   rather than hidden.
5. quiz_id vs. session_id. The spec's event-tracking list names Quiz ID;
   internally this is the quiz session id (quiz_sessions._id), since a
   "quiz" in this app is a stateful session (sampled question order +
   progression pointer), not a static entity.
6. Auth model. Dummy login only, per the spec - selecting a predefined user
   returns their id as a session_token. No JWT, no password. Login still
   has real product meaning via the My Progress / Cohort Analytics split
   and server-side session-ownership enforcement (see above), without
   introducing a permissions system the assignment doesn't ask for.
7. Cohort Analytics is not access-restricted to an admin role. The
   assignment specifies analytics APIs but no admin/role concept. Rather
   than invent one, Cohort Analytics is available to any logged-in user but
   clearly labeled as cross-learner data, distinct from My Progress.

## What was deliberately left out

Per the assignment's own guidance ("we are not evaluating how quickly you
can scaffold CRUD") and the 4-day scope: no Redis/Kafka/microservices/CQRS/
background workers/WebSockets, no production auth or admin role system, no
z-score/winsorization/ML in the analytics, no speculative indexes on
collections with <=10 documents, no runtime LLM or external API calls for
question generation.

## Status of this submission

The repository and the supplied assignment PDF were inspected before the final
polish pass. The PDF is the requirements source of truth: it specifies React,
FastAPI, MongoDB, dummy login, one-question-at-a-time MCQs, server-enforced
no-revisit progression, event tracking, and three explicitly named analytics
metrics despite calling them "four analytics APIs".

The current implementation was preserved rather than rebuilt. Recent polish
passes have focused on the personal-vs-cohort product split, question-level
personal fatigue progression, readable response times, denser analytics
visualizations, quiz UX, navigation, empty/error states, dead-code/doc
cleanup, and visual consistency.

**The full backend test suite has been run locally (not just in a sandbox)
and passed: 104/104 tests green**, covering formulas, quiz progression,
no-revisit/duplicate-submit rejection, session ownership, the `shown_at`
idempotency fix, all three analytics APIs against deterministic fixtures,
My Progress scoping, and seed-content correctness (question shape,
determinism, no placeholder text).

If you're verifying in a fresh environment:

```bash
cd backend
pip install -r requirements.txt
pytest -q

cd ../frontend
npm install
npm run build
```

For an end-to-end run:

```bash
docker compose up --build
docker compose exec backend python scripts/seed.py
```

Then verify the browser flow: login -> My Progress -> Exam -> Subject ->
Chapter -> Quiz -> Result -> My Progress -> Cohort Analytics.

## Loom walkthrough checklist

- [ ] Project structure walkthrough (this README's structure section)
- [ ] Login -> My Progress, showing it's scoped to just this learner
- [ ] Exam -> Subject -> Chapter -> Quiz -> Result, showing no-revisit and
      real (non-placeholder) question content
- [ ] Cohort Analytics: LVI leaderboard, fatigue browser, difficulty ranking
- [ ] Log in as 2-3 of the seed script's printed "Demo users" and show
      their My Progress charts look visibly different from each other
- [ ] Database design + why (denormalized ancestry fields, reference vs.
      embedding decision, index table)
- [ ] Analytics implementation: pipelines.py (Mongo side) vs. formulas.py
      (pure Python scoring), and the "How is this calculated?" panels
- [ ] Assumptions section (especially #1 - the "four vs. three" discrepancy,
      and #6/#7 - the login/analytics scoping decision)