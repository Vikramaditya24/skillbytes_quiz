# SkillBytes Quiz Application

A full-stack quiz and learning analytics platform built for the SkillBytes Junior Full Stack Developer assessment.

**Live application**
- Frontend: https://skillbytes-quiz-delta.vercel.app/
- Backend: https://skillbytes-quiz-na42.onrender.com
- Repository: https://github.com/Vikramaditya24/skillbytes_quiz
- Walkthrough: https://www.loom.com/share/8bc22a1a4eb94fa8ba846893a6150e30

## Overview

The application implements the complete learner flow:

**Login → My Progress → Exam → Subject → Chapter → Quiz → Result**

It also provides a separate **Cohort Analytics** area containing the three analytics metrics explicitly described in the assignment:

1. Learning Velocity Index
2. Fatigue Analysis
3. Question Difficulty Index

The backend is built with **FastAPI + MongoDB** and the frontend with **React + Vite**.

The implementation intentionally follows the assignment's dummy-auth requirement rather than introducing unnecessary production authentication.

## Tech Stack

### Frontend
- React
- Vite
- React Router
- Charting library
- Responsive UI

### Backend
- Python
- FastAPI
- Pydantic
- Motor / PyMongo
- MongoDB
- pytest
- mongomock-motor

### Architecture

```text
React
  ↓
API layer
  ↓
FastAPI routers
  ↓
Services
  ↓
Repositories
  ↓
MongoDB
```

Analytics use a separate path:

```text
MongoDB question_attempts
        ↓
Mongo aggregation pipelines
        ↓
Grouped metrics
        ↓
Pure Python scoring formulas
        ↓
Analytics API
        ↓
React visualizations
```

The repository follows a **Router → Service → Repository** dependency direction.

Simple catalog reads intentionally bypass the service layer where there is no business logic. Services are used where actual orchestration or business rules exist, particularly quiz progression and analytics.

## Project Structure

```text
/
├── backend/
│   ├── app/
│   │   ├── api/              # FastAPI routers
│   │   ├── services/         # Quiz and analytics business logic
│   │   ├── repositories/     # MongoDB access layer
│   │   ├── schemas/          # Pydantic request/response models
│   │   ├── core/             # Settings, DB connection, indexes
│   │   └── aggregations/     # Mongo pipelines and pure scoring formulas
│   ├── scripts/
│   │   ├── seed.py           # Deterministic database seed
│   │   └── question_bank.py  # Deterministic MCQ generator
│   └── tests/
│
├── frontend/
│   └── src/
│       ├── pages/            # Application pages
│       └── api/              # API client
│
├── docker-compose.yml
└── README.md
```

## Running Locally

### Option A — Docker

Copy the example environment file:

```bash
cp backend/.env.example backend/.env
```

Then:

```bash
docker compose up --build
```

Services:

```text
Frontend: http://localhost:5173
Backend:  http://localhost:8000
API docs: http://localhost:8000/docs
MongoDB:  localhost:27017
```

Seed the database:

```bash
docker compose exec backend python scripts/seed.py
```

The seed script is deterministic and can safely be rerun when a fresh dataset is required.

### Option B — Local development without Docker

Requirements:

- Python 3.11+
- Node.js 20+
- MongoDB

Backend:

```bash
cd backend
python -m venv .venv
```

Windows:

```bash
.venv\Scripts\activate
```

macOS/Linux:

```bash
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Seed MongoDB:

```bash
python scripts/seed.py
```

Run the API:

```bash
uvicorn app.main:app --reload
```

In another terminal:

```bash
cd frontend
npm install
npm run dev
```

## Testing

Run the backend test suite:

```bash
cd backend
pytest -q
```

The test suite uses `mongomock-motor` for database-backed tests, so a real MongoDB instance is not required for the normal test run.

The suite covers:

- Analytics formulas
- Learning Velocity Index
- Fatigue Analysis
- Question Difficulty Index
- Analytics aggregation behavior
- Quiz progression
- Question ordering
- Server-side no-revisit enforcement
- Duplicate answer rejection
- Session ownership
- `shown_at` timestamp idempotency
- Personal progress scoping
- Dummy login
- Event structure
- Seed data correctness
- Deterministic seed behavior
- Question-bank validity
- Placeholder-content checks
- Internal seed metadata not leaking through APIs

The final local backend suite passes:

```text
104 passed
```

Frontend production build:

```bash
cd frontend
npm install
npm run build
```

## Product Flow

### Login

The assignment specifies dummy login, so users select from seeded learners rather than entering passwords.

After login, the learner is taken to **My Progress**.

### My Progress

My Progress is learner-specific.

It shows:

- Learning Velocity Index
- Accuracy
- Recent quiz history
- Personal fatigue progression
- Explanations of the metrics

A learner can only see their own progress.

### Quiz

The quiz flow is:

```text
Exam
  ↓
Subject
  ↓
Chapter
  ↓
Quiz
  ↓
One question at a time
  ↓
Result
```

The frontend does not determine which question comes next.

The backend owns the progression state.

### Cohort Analytics

Cohort Analytics is intentionally separate from My Progress.

It provides comparative views across learners:

- LVI leaderboard
- Fatigue analysis
- Question difficulty ranking

The distinction is explicit in the UI:

```text
My Progress       = you
Cohort Analytics  = everyone
```

No admin role was invented because the assignment does not define one.

## Session Ownership and Server-Side Enforcement

Every session-scoped operation verifies that the authenticated user's `user_id` matches the owner stored in the quiz session.

This applies to:

- Current question
- Answer submission
- Result retrieval

A learner therefore cannot access or modify another learner's quiz session simply by changing the session ID.

The backend returns HTTP 403 when ownership validation fails.

This is particularly important because the assignment uses dummy authentication.

## No-Revisit Enforcement

Quiz progression is server-controlled.

`quiz_sessions.current_index` is the authoritative pointer to the current question.

The server rejects attempts to answer:

- A previous question
- A future question
- A question other than the current question

The index is advanced atomically so concurrent or duplicate requests cannot incorrectly advance the quiz.

There is also a database-level unique index on:

```text
(session_id, question_id)
```

This provides a second backstop against duplicate submissions.

## `shown_at` Timestamp Idempotency

Response time is calculated from the server-side `shown_at` timestamp.

An important edge case was handled explicitly:

A browser refresh or repeated request for the current question must not reset the timestamp.

The implementation therefore only creates the timestamp if it does not already exist.

This prevents a learner from accidentally or intentionally changing their measured response time simply by refreshing the page.

A regression test covers this behavior.

## Database Design

The main MongoDB collections are:

```text
users
exams
subjects
chapters
questions
quiz_sessions
question_attempts
```

### `question_attempts` as the event source

`question_attempts` is treated as the canonical immutable event stream.

It contains the information required to calculate the analytics metrics.

Analytics never write derived results back into the event collection.

This keeps the analytics reproducible from the underlying events.

### References vs embedding

Relationships are represented using IDs rather than embedding large nested structures.

This is particularly important for `question_attempts`, which is a high-write, high-cardinality event collection.

Embedding attempts inside users or quiz sessions would create unnecessarily large mutable documents and make analytics less natural.

### Deliberate denormalization

Questions and attempts carry:

```text
exam_id
subject_id
chapter_id
```

in addition to their immediate relationship.

This is deliberate denormalization.

The hierarchy is immutable, so duplicating these scalar ancestry fields allows analytics pipelines to filter directly without repeatedly performing:

```text
attempt → question → chapter → subject → exam
```

## Indexes

The application creates indexes based on actual access patterns.

| Collection | Index | Purpose |
|---|---|---|
| questions | `{ chapter_id: 1 }` | Sampling chapter questions |
| quiz_sessions | `{ user_id: 1, status: 1 }` | Active/recent session lookups |
| question_attempts | `{ session_id: 1, question_id: 1 }` unique | Duplicate/revisit protection |
| question_attempts | `{ user_id: 1, session_id: 1, question_sequence_number: 1 }` | User/session analytics windowing |
| question_attempts | `{ question_id: 1 }` | Question difficulty aggregation |

Small lookup collections do not receive speculative indexes simply for completeness.

# Analytics

All three analytics metrics operate from `question_attempts`.

MongoDB performs grouping and aggregation where appropriate. The resulting grouped data is passed to isolated Python formula functions.

This separation makes the statistical logic independently testable.

## 1. Learning Velocity Index

### Accuracy

```text
accuracy = correct_attempts / total_attempts × 100
```

### Speed score

Speed is normalized relative to the observed response-time range for the cohort.

```text
fastest observed time → 100
slowest observed time  → 0
```

If the observed range is zero, or there is only one observation, the score falls back to a neutral value of 50 rather than dividing by zero.

### Consistency

Consistency uses the coefficient of variation:

```text
CV = standard_deviation / mean
```

Then:

```text
consistency = 100 / (1 + CV)
```

For insufficient data, the implementation does not fabricate a statistically meaningful value. The UI marks the result as insufficient data.

### LVI

The composite score is:

```text
LVI =
    50% accuracy
  + 30% speed
  + 20% consistency
```

Accuracy intentionally carries the greatest weight.

The design goal is that speed and consistency refine the ranking rather than allowing a significantly less accurate learner to automatically outrank a highly accurate learner simply because they answer slightly faster.

The weights are named configuration constants rather than magic numbers.

## 2. Fatigue Analysis

Attempts are grouped into fixed question windows.

The default is:

```text
Questions 1–5
Questions 6–10
Questions 11–15
```

The window size is configurable.

Each later window is compared with that learner's own first window.

A fatigue flag is raised only when both conditions occur:

```text
accuracy decreases by >5 percentage points
AND
average response time increases by >10%
```

This avoids labeling a learner as fatigued solely because later questions happen to be more difficult.

The metric is presented as a descriptive heuristic rather than a scientific or causal diagnosis.

## 3. Question Difficulty Index

Question difficulty combines two signals:

```text
70% inverted accuracy
+
30% relative response-time difficulty
```

Inverted accuracy:

```text
100 - question accuracy
```

Response time is normalized within the question's chapter so that an inherently slower chapter does not automatically make all of its questions appear more difficult than questions from faster chapters.

The purpose is to identify questions that are both:

- frequently answered incorrectly
- relatively time-consuming

## Analytics Explainability

The UI includes plain-language explanations of how each metric is calculated.

This is intentional: an evaluator should be able to understand the meaning and limitations of the metrics without inspecting the implementation.

# Seed Data

The seed script creates a deterministic demonstration dataset.

The random seed is fixed, so repeated runs produce reproducible data.

The dataset contains:

- 50 learners
- 3 exams
- 10 subjects
- 30 chapters
- 500 questions

Six behavioral archetypes are represented:

```text
high_accuracy_fast
high_accuracy_slow
improving
declining
inconsistent
low_accuracy
```

The archetype is stored internally as `_archetype` and is never returned through the API.

Names are generated independently of behavioral archetype so that a learner's name does not reveal their analytics profile.

The seed script also creates several stronger "hero" profiles with additional completed sessions so that the different behavioral patterns are easy to demonstrate during the application walkthrough.

## Question Bank

The question bank is deterministic and template-based.

It does not call an LLM or external API at runtime.

The generated content includes:

- Mathematics
- Science
- History
- Biology
- Chemistry
- Political Science
- Grammar
- Vocabulary

Numerical subjects use deterministic parameterized calculations and plausible distractors.

Fact-based subjects use curated fact banks with multiple phrasing variants.

Tests verify:

- exactly four options per question
- exactly one correct option
- no duplicate question text within a chapter
- no leftover placeholder content
- deterministic output

# Authentication

Authentication is intentionally simple because the assignment specifies dummy login.

There are:

- no passwords
- no JWT implementation
- no external identity provider
- no role/permission system

Selecting a predefined learner establishes the current learner identity.

The application nevertheless enforces session ownership server-side.

This provides meaningful authorization behavior without introducing authentication infrastructure that the assignment did not request.

# Deployment

The deployed application uses:

```text
Frontend → Vercel
Backend  → Render
Database → MongoDB Atlas
```

Frontend:

https://skillbytes-quiz-delta.vercel.app/

Backend:

https://skillbytes-quiz-na42.onrender.com

The React application includes SPA fallback routing so direct navigation and browser refreshes on client-side routes continue to work correctly.

# Assignment Decisions / Assumptions

### 1. "Four analytics APIs" vs three named metrics

The assignment refers to "four analytics APIs", but explicitly describes only three:

1. Learning Velocity Index
2. Fatigue Analysis
3. Question Difficulty Index

No fourth metric is named elsewhere in the requirements.

The implementation therefore follows the three explicitly specified metrics rather than inventing an undocumented fourth metric.

### 2. Quiz session size

A quiz samples up to 15 questions from the selected chapter.

This matches the assignment's fatigue-analysis example of:

```text
1–5
6–10
11–15
```

### 3. Timestamp authority

`shown_at` and `answered_at` are generated server-side.

Therefore response time is measured from the server's perspective and includes network/request latency.

This is preferable to trusting a client-provided duration.

### 4. Quiz ID vs session ID

The assignment refers to Quiz ID in its event-tracking requirements.

Internally, the application treats a quiz as a stateful quiz session because the session contains:

- selected question order
- current position
- progression state

Therefore `quiz_session._id` acts as the quiz/session identifier.

### 5. Cohort analytics access

Cohort Analytics is available to logged-in users.

The assignment defines comparative analytics but does not specify an administrator role.

Introducing a separate admin authentication system would therefore add complexity without satisfying an explicit requirement.

# What Is Deliberately Not Included

This is an assessment project rather than a production SaaS platform.

The implementation intentionally does not introduce:

- Redis
- Kafka
- microservices
- CQRS
- WebSockets
- background workers
- production-grade authentication
- role-based administration
- ML-based analytics
- runtime LLM calls
- speculative database indexes
- unnecessary CRUD abstraction

The goal was to demonstrate sound full-stack engineering and analytical reasoning within the assignment's scope.

# Verification

A fresh environment can be verified with:

```bash
cd backend
pip install -r requirements.txt
pytest -q
```

Then:

```bash
cd ../frontend
npm install
npm run build
```

For a full local environment:

```bash
docker compose up --build
docker compose exec backend python scripts/seed.py
```

Recommended browser verification:

```text
Login
  ↓
My Progress
  ↓
Exam
  ↓
Subject
  ↓
Chapter
  ↓
Quiz
  ↓
Result
  ↓
My Progress
  ↓
Cohort Analytics
```

Also verify:

- browser refresh on client-side routes
- direct navigation to a nested route
- opening another user's quiz session URL
- attempting to submit an answer to another user's session
- repeated refreshes of the current question
- duplicate answer submission
- completion and result retrieval
- switching between different seeded users

# Submission

**Repository**

https://github.com/Vikramaditya24/skillbytes_quiz

**Frontend**

https://skillbytes-quiz-delta.vercel.app/

**Backend**

https://skillbytes-quiz-na42.onrender.com

**API documentation**

`https://skillbytes-quiz-na42.onrender.com/docs`

**Walkthrough**

https://www.loom.com/share/8bc22a1a4eb94fa8ba846893a6150e30

The implementation was developed against the supplied SkillBytes assignment requirements, with particular attention to server-side quiz enforcement, event-based analytics, explainable formulas, deterministic seed data, personal-vs-cohort analytics separation, and test coverage.
