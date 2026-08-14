"""
Deterministic seed script (fixed random seed - reruns produce identical data,
per Milestone 0's "deterministic" requirement).

Populates:
  - 50 users, 3 exams, 10 subjects (3/3/4 split), 30 chapters, 500 questions
  - Completed quiz_sessions + question_attempts for every user, generated
    from 6 named behavioral archetypes so the analytics dashboard shows real,
    recognizable differences instead of uniform noise:
      high_accuracy_fast, high_accuracy_slow, low_accuracy_fast, inconsistent,
      improving (accuracy rises / time falls across the session),
      declining (accuracy falls / time rises across the session - classic
      fatigue signature, used to sanity-check the Fatigue Analysis API).

Run: python scripts/seed.py
"""

import asyncio
import random
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from motor.motor_asyncio import AsyncIOMotorClient  # noqa: E402

from app.core.config import settings  # noqa: E402
from app.core.db import create_indexes  # noqa: E402

RNG_SEED = 42
N_USERS = 50
N_EXAMS = 3
N_SUBJECTS = 10
N_CHAPTERS = 30
N_QUESTIONS = 500
SUBJECTS_PER_EXAM = [3, 3, 4]  # sums to 10 - see Milestone 0 B2
QUESTIONS_PER_CHAPTER = N_QUESTIONS // N_CHAPTERS  # even split, remainder added to last chapters

ARCHETYPES = [
    "high_accuracy_fast",
    "high_accuracy_slow",
    "low_accuracy_fast",
    "inconsistent",
    "improving",
    "declining",
]

FIRST_NAMES = [
    "Aarav", "Vivaan", "Aditi", "Diya", "Ishaan", "Ananya", "Kabir", "Meera",
    "Rohan", "Sara", "Arjun", "Priya", "Karan", "Neha", "Aryan", "Isha",
    "Dev", "Riya", "Yash", "Tara", "Nikhil", "Pooja", "Rahul", "Simran",
    "Aman", "Kiara", "Varun", "Anika", "Sameer", "Naina", "Vikram", "Aisha",
    "Raj", "Zara", "Mohit", "Lara", "Suresh", "Nidhi", "Harsh", "Fatima",
    "Om", "Radhika", "Siddharth", "Maya", "Tanvi", "Aakash", "Bhavna",
    "Chirag", "Deepa", "Eshan",
]

SUBJECT_NAMES = [
    "Algebra", "Geometry", "Mechanics", "Thermodynamics", "Organic Chemistry",
    "Cell Biology", "Modern History", "Political Science", "Grammar", "Vocabulary",
]

EXAM_NAMES = ["JEE Foundation", "NEET Foundation", "General Aptitude"]


def make_options(correct_idx: int) -> tuple[list[dict], str]:
    keys = ["A", "B", "C", "D"]
    options = [{"key": k, "text": f"Option {k}"} for k in keys]
    return options, keys[correct_idx]


async def seed() -> None:
    rng = random.Random(RNG_SEED)
    client = AsyncIOMotorClient(settings.mongo_uri)
    db = client[settings.mongo_db_name]

    print(f"Dropping database '{settings.mongo_db_name}' for a clean deterministic seed...")
    await client.drop_database(settings.mongo_db_name)

    # --- Users ---
    users = [
        {"name": f"{FIRST_NAMES[i]} User{i+1}", "email": f"user{i+1}@skillbytes.test",
         "created_at": datetime.now(timezone.utc)}
        for i in range(N_USERS)
    ]
    user_ids = (await db.users.insert_many(users)).inserted_ids
    print(f"Inserted {len(user_ids)} users")

    # --- Exams ---
    exams = [{"name": EXAM_NAMES[i], "description": f"{EXAM_NAMES[i]} exam"} for i in range(N_EXAMS)]
    exam_ids = (await db.exams.insert_many(exams)).inserted_ids

    # --- Subjects (3/3/4 split across exams) ---
    subject_docs = []
    subject_name_idx = 0
    exam_for_subject = []
    for exam_idx, count in enumerate(SUBJECTS_PER_EXAM):
        for _ in range(count):
            subject_docs.append(
                {"exam_id": str(exam_ids[exam_idx]), "name": SUBJECT_NAMES[subject_name_idx]}
            )
            exam_for_subject.append(str(exam_ids[exam_idx]))
            subject_name_idx += 1
    subject_ids = (await db.subjects.insert_many(subject_docs)).inserted_ids
    print(f"Inserted {len(subject_ids)} subjects")

    # --- Chapters (30 total, 3 per subject) ---
    chapter_docs = []
    chapter_owner_subject = []
    chapters_per_subject = N_CHAPTERS // N_SUBJECTS
    for s_idx, subject in enumerate(subject_docs):
        for c in range(chapters_per_subject):
            chapter_docs.append(
                {
                    "subject_id": str(subject_ids[s_idx]),
                    "exam_id": subject["exam_id"],
                    "name": f"{subject['name']} - Chapter {c + 1}",
                }
            )
            chapter_owner_subject.append(s_idx)
    chapter_ids = (await db.chapters.insert_many(chapter_docs)).inserted_ids
    print(f"Inserted {len(chapter_ids)} chapters")

    # --- Questions (~17 per chapter, remainder to last chapters) ---
    question_docs = []
    chapter_question_ids: dict[str, list[str]] = {str(cid): [] for cid in chapter_ids}
    remaining = N_QUESTIONS
    for i, chapter in enumerate(chapter_docs):
        chapters_left = N_CHAPTERS - i
        count = remaining // chapters_left
        remaining -= count
        for q in range(count):
            options, correct_key = make_options(rng.randint(0, 3))
            question_docs.append(
                {
                    "chapter_id": str(chapter_ids[i]),
                    "subject_id": chapter["subject_id"],
                    "exam_id": chapter["exam_id"],
                    "text": f"{chapter['name']} — Question {q + 1}: which statement is correct?",
                    "options": options,
                    "correct_option_key": correct_key,
                    "created_at": datetime.now(timezone.utc),
                }
            )
    result = await db.questions.insert_many(question_docs)
    question_by_id: dict[str, dict] = {}
    for qid, qdoc in zip(result.inserted_ids, question_docs):
        chapter_question_ids[qdoc["chapter_id"]].append(str(qid))
        question_by_id[str(qid)] = qdoc
    print(f"Inserted {len(result.inserted_ids)} questions")

    # --- Sessions + attempts, driven by behavioral archetypes ---
    archetype_params = {
        # (base_accuracy, min_ms, max_ms, trend)
        # trend: None | "improving" | "declining"
        "high_accuracy_fast": dict(base_acc=0.90, min_ms=2500, max_ms=5000, jitter=400, trend=None),
        "high_accuracy_slow": dict(base_acc=0.88, min_ms=9000, max_ms=13000, jitter=600, trend=None),
        "low_accuracy_fast": dict(base_acc=0.35, min_ms=2200, max_ms=4200, jitter=400, trend=None),
        "inconsistent": dict(base_acc=0.60, min_ms=2000, max_ms=16000, jitter=4000, trend=None),
        "improving": dict(base_acc=0.45, min_ms=8000, max_ms=11000, jitter=500, trend="improving"),
        "declining": dict(base_acc=0.85, min_ms=3000, max_ms=5000, jitter=500, trend="declining"),
    }

    session_docs = []
    attempt_docs = []
    session_id_counter = 0
    now = datetime.now(timezone.utc)

    for u_idx, user_id in enumerate(user_ids):
        archetype = ARCHETYPES[u_idx % len(ARCHETYPES)]
        params = archetype_params[archetype]
        n_sessions = rng.choice([2, 3])

        for s in range(n_sessions):
            chapter_idx = rng.randrange(N_CHAPTERS)
            chapter = chapter_docs[chapter_idx]
            chapter_id = str(chapter_ids[chapter_idx])
            pool = chapter_question_ids[chapter_id]
            sample_size = min(settings.quiz_session_size, len(pool))
            sampled_qids = rng.sample(pool, sample_size)

            session_started = now - timedelta(days=rng.randint(0, 20), hours=rng.randint(0, 12))
            cursor_time = session_started
            correct_count = 0
            local_attempts = []

            for seq, qid in enumerate(sampled_qids, start=1):
                q = question_by_id[qid]
                # progress fraction through this session, 0..1
                progress = (seq - 1) / max(sample_size - 1, 1)

                acc = params["base_acc"]
                mean_ms = (params["min_ms"] + params["max_ms"]) / 2
                spread = (params["max_ms"] - params["min_ms"]) / 2

                if params["trend"] == "declining":
                    acc = max(0.05, params["base_acc"] - 0.5 * progress)
                    mean_ms = mean_ms + spread * 1.4 * progress
                elif params["trend"] == "improving":
                    acc = min(0.97, params["base_acc"] + 0.5 * progress)
                    mean_ms = mean_ms - spread * 0.8 * progress

                is_correct = rng.random() < acc
                response_ms = max(500, int(rng.gauss(mean_ms, params["jitter"])))

                shown_at = cursor_time
                answered_at = shown_at + timedelta(milliseconds=response_ms)
                cursor_time = answered_at + timedelta(seconds=1)  # small gap before next question shown

                selected_key = q["correct_option_key"] if is_correct else rng.choice(
                    [o["key"] for o in q["options"] if o["key"] != q["correct_option_key"]]
                )

                local_attempts.append(
                    {
                        "session_id": None,  # filled after session insert
                        "user_id": str(user_id),
                        "question_id": qid,
                        "exam_id": q["exam_id"],
                        "subject_id": q["subject_id"],
                        "chapter_id": q["chapter_id"],
                        "question_sequence_number": seq,
                        "shown_at": shown_at,
                        "answered_at": answered_at,
                        "response_duration_ms": response_ms,
                        "selected_option_key": selected_key,
                        "is_correct": is_correct,
                    }
                )
                if is_correct:
                    correct_count += 1

            session_docs.append(
                {
                    "user_id": str(user_id),
                    "exam_id": chapter["exam_id"],
                    "subject_id": chapter["subject_id"],
                    "chapter_id": chapter_id,
                    "question_ids": sampled_qids,
                    "current_index": sample_size,
                    "status": "completed",
                    "score": correct_count,
                    "total_questions": sample_size,
                    "started_at": session_started,
                    "completed_at": cursor_time,
                    "_archetype": archetype,  # informational only, harmless extra field
                }
            )
            session_id_counter += 1
            session_docs[-1]["_local_attempts"] = local_attempts

    # Insert sessions, then backfill session_id on attempts and insert them.
    for doc in session_docs:
        local_attempts = doc.pop("_local_attempts")
        inserted = await db.quiz_sessions.insert_one(doc)
        sid = str(inserted.inserted_id)
        for a in local_attempts:
            a["session_id"] = sid
        attempt_docs.extend(local_attempts)

    if attempt_docs:
        await db.question_attempts.insert_many(attempt_docs)
    print(f"Inserted {len(session_docs)} quiz sessions and {len(attempt_docs)} question attempts")

    await create_indexes(db)
    print("Indexes created")

    client.close()
    print("Seed complete.")


if __name__ == "__main__":
    asyncio.run(seed())
