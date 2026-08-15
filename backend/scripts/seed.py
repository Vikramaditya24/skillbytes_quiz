"""
Deterministic seed script (fixed RNG seed - reruns produce identical data).

Populates:
  - 50 users with realistic names/emails (archetype is an internal-only field,
    never surfaced to the frontend - see app/schemas/user.py UserOut, which
    has no archetype field)
  - 3 exams, 10 subjects (3/3/4 split), 30 chapters, 500 questions - generated
    via scripts/question_bank.py's deterministic subject-specific templates,
    not placeholder text
  - Completed quiz_sessions + question_attempts for every user, generated
    from 6 named behavioral archetypes. The FIRST user assigned to each
    archetype is a "hero" user: more sessions and a stronger, cleaner signal,
    specifically so a single learner's own charts (not just the cohort
    ranking) visibly demonstrate that pattern - see the printed "Demo users"
    list at the end of this script's output for who to log in as.

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
from scripts.question_bank import generate_question  # noqa: E402

RNG_SEED = 42
N_USERS = 50
N_EXAMS = 3
N_SUBJECTS = 10
N_CHAPTERS = 30
N_QUESTIONS = 500
SUBJECTS_PER_EXAM = [3, 3, 4]  # sums to 10 - see README > Assumptions B2

ARCHETYPES = [
    "high_accuracy_fast",
    "high_accuracy_slow",
    "improving",
    "declining",
    "inconsistent",
    "low_accuracy",
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

LAST_NAMES = [
    "Sharma", "Nair", "Verma", "Iyer", "Gupta", "Reddy", "Kapoor", "Menon",
    "Joshi", "Malhotra", "Chatterjee", "Rao", "Bose", "Pillai", "Desai",
    "Agarwal", "Mehta", "Kulkarni", "Bhatt", "Chawla", "Saxena", "Bansal",
    "Krishnan", "Suresh", "Thakur",
]

SUBJECT_NAMES = [
    "Algebra", "Geometry", "Mechanics", "Thermodynamics", "Organic Chemistry",
    "Cell Biology", "Modern History", "Political Science", "Grammar", "Vocabulary",
]

EXAM_NAMES = ["JEE Foundation", "NEET Foundation", "General Aptitude"]


def build_user_identities(rng: random.Random, count: int) -> list[dict]:
    """
    Deterministic, realistic name+email pairs. Names are drawn independently
    of archetype assignment (see assign_archetypes) so there is no pattern
    linking a display name to a behavioral profile.
    """
    first_pool = list(FIRST_NAMES)
    last_pool = list(LAST_NAMES)
    rng.shuffle(first_pool)
    rng.shuffle(last_pool)

    identities = []
    used_emails: set[str] = set()
    for i in range(count):
        first = first_pool[i % len(first_pool)]
        last = last_pool[(i * 7 + 3) % len(last_pool)]  # decorrelate from first-name cycling
        name = f"{first} {last}"
        base_email = f"{first.lower()}.{last.lower()}@learnhub.test"
        email = base_email
        suffix = 2
        while email in used_emails:
            email = f"{first.lower()}.{last.lower()}{suffix}@learnhub.test"
            suffix += 1
        used_emails.add(email)
        identities.append({"name": name, "email": email})
    return identities


def assign_archetypes(count: int) -> list[str]:
    """Cycle archetypes by user index - independent of name/email assignment above."""
    return [ARCHETYPES[i % len(ARCHETYPES)] for i in range(count)]


async def seed() -> None:
    rng = random.Random(RNG_SEED)
    client = AsyncIOMotorClient(settings.mongo_uri, tz_aware=True)  # keep in sync with core/db.py
    db = client[settings.mongo_db_name]

    print(f"Dropping database '{settings.mongo_db_name}' for a clean deterministic seed...")
    await client.drop_database(settings.mongo_db_name)

    # --- Users: realistic identities, archetype kept internal-only ---
    identities = build_user_identities(rng, N_USERS)
    archetypes = assign_archetypes(N_USERS)
    users = [
        {
            "name": identities[i]["name"],
            "email": identities[i]["email"],
            "created_at": datetime.now(timezone.utc),
            "_archetype": archetypes[i],  # internal only - never in UserOut/API responses
        }
        for i in range(N_USERS)
    ]
    user_ids = (await db.users.insert_many(users)).inserted_ids
    print(f"Inserted {len(user_ids)} users")

    # Track the first user per archetype as the "hero" demo user for that pattern.
    hero_user_index_by_archetype: dict[str, int] = {}
    for i, a in enumerate(archetypes):
        hero_user_index_by_archetype.setdefault(a, i)

    # --- Exams ---
    exams = [{"name": EXAM_NAMES[i], "description": f"{EXAM_NAMES[i]} exam"} for i in range(N_EXAMS)]
    exam_ids = (await db.exams.insert_many(exams)).inserted_ids

    # --- Subjects (3/3/4 split across exams) ---
    subject_docs = []
    subject_name_idx = 0
    for exam_idx, count in enumerate(SUBJECTS_PER_EXAM):
        for _ in range(count):
            subject_docs.append(
                {"exam_id": str(exam_ids[exam_idx]), "name": SUBJECT_NAMES[subject_name_idx]}
            )
            subject_name_idx += 1
    subject_ids = (await db.subjects.insert_many(subject_docs)).inserted_ids
    print(f"Inserted {len(subject_ids)} subjects")

    # --- Chapters (30 total, 3 per subject) ---
    chapter_docs = []
    chapters_per_subject = N_CHAPTERS // N_SUBJECTS
    for s_idx, subject in enumerate(subject_docs):
        for c in range(chapters_per_subject):
            chapter_docs.append(
                {
                    "subject_id": str(subject_ids[s_idx]),
                    "exam_id": subject["exam_id"],
                    "name": f"{subject['name']} - Chapter {c + 1}",
                    "_subject_name": subject["name"],  # local helper, stripped before insert
                }
            )
    chapter_ids = (
        await db.chapters.insert_many(
            [{k: v for k, v in c.items() if not k.startswith("_")} for c in chapter_docs]
        )
    ).inserted_ids
    print(f"Inserted {len(chapter_ids)} chapters")

    # --- Questions: real, subject-appropriate MCQs via question_bank generators ---
    question_docs = []
    chapter_question_ids: dict[str, list[str]] = {str(cid): [] for cid in chapter_ids}
    remaining = N_QUESTIONS
    for i, chapter in enumerate(chapter_docs):
        chapters_left = N_CHAPTERS - i
        count = remaining // chapters_left
        remaining -= count
        subject_name = chapter["_subject_name"]
        chapter_local_idx = i % chapters_per_subject  # 0, 1, or 2 within its subject
        for q in range(count):
            generated = generate_question(subject_name, chapter_local_idx, q, rng)
            question_docs.append(
                {
                    "chapter_id": str(chapter_ids[i]),
                    "subject_id": chapter["subject_id"],
                    "exam_id": chapter["exam_id"],
                    "text": generated["text"],
                    "options": generated["options"],
                    "correct_option_key": generated["correct_option_key"],
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
    # base_acc/min_ms/max_ms/jitter/trend describe the *non-hero* population;
    # hero users (see below) get an amplified version of the same profile so
    # their individual charts are unambiguous on their own, not just in the
    # cohort ranking.
    archetype_params = {
        "high_accuracy_fast": dict(base_acc=0.90, min_ms=2500, max_ms=5000, jitter=350, trend=None),
        "high_accuracy_slow": dict(base_acc=0.88, min_ms=9500, max_ms=13000, jitter=500, trend=None),
        "improving": dict(base_acc=0.40, min_ms=8500, max_ms=11000, jitter=450, trend="improving"),
        "declining": dict(base_acc=0.88, min_ms=3000, max_ms=4500, jitter=400, trend="declining"),
        "inconsistent": dict(base_acc=0.60, min_ms=2000, max_ms=17000, jitter=4500, trend=None),
        "low_accuracy": dict(base_acc=0.30, min_ms=3000, max_ms=5500, jitter=500, trend=None),
    }
    HERO_AMPLIFICATION = {
        # multiplies the effect size for the hero user of each archetype
        "high_accuracy_fast": dict(acc_boost=0.05, time_scale=0.85),
        "high_accuracy_slow": dict(acc_boost=0.05, time_scale=1.15),
        "improving": dict(trend_strength=1.4),
        "declining": dict(trend_strength=1.4),
        "inconsistent": dict(jitter_scale=1.3),
        "low_accuracy": dict(acc_penalty=0.10),
    }

    session_docs = []
    attempt_docs = []
    now = datetime.now(timezone.utc)

    for u_idx, user_id in enumerate(user_ids):
        archetype = archetypes[u_idx]
        params = dict(archetype_params[archetype])
        is_hero = hero_user_index_by_archetype[archetype] == u_idx

        if is_hero:
            amp = HERO_AMPLIFICATION[archetype]
            if "acc_boost" in amp:
                params["base_acc"] = min(0.98, params["base_acc"] + amp["acc_boost"])
            if "acc_penalty" in amp:
                params["base_acc"] = max(0.10, params["base_acc"] - amp["acc_penalty"])
            if "time_scale" in amp:
                params["min_ms"] = int(params["min_ms"] * amp["time_scale"])
                params["max_ms"] = int(params["max_ms"] * amp["time_scale"])
            if "jitter_scale" in amp:
                params["jitter"] = int(params["jitter"] * amp["jitter_scale"])
            trend_strength = amp.get("trend_strength", 1.0)
        else:
            trend_strength = 1.0

        n_sessions = 5 if is_hero else rng.choice([2, 3])

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
                progress = (seq - 1) / max(sample_size - 1, 1)

                acc = params["base_acc"]
                mean_ms = (params["min_ms"] + params["max_ms"]) / 2
                spread = (params["max_ms"] - params["min_ms"]) / 2

                if params["trend"] == "declining":
                    acc = max(0.05, params["base_acc"] - 0.5 * trend_strength * progress)
                    mean_ms = mean_ms + spread * 1.4 * trend_strength * progress
                elif params["trend"] == "improving":
                    acc = min(0.97, params["base_acc"] + 0.5 * trend_strength * progress)
                    mean_ms = mean_ms - spread * 0.8 * trend_strength * progress

                is_correct = rng.random() < acc
                response_ms = max(500, int(rng.gauss(mean_ms, params["jitter"])))

                shown_at = cursor_time
                answered_at = shown_at + timedelta(milliseconds=response_ms)
                cursor_time = answered_at + timedelta(seconds=1)

                selected_key = q["correct_option_key"] if is_correct else rng.choice(
                    [o["key"] for o in q["options"] if o["key"] != q["correct_option_key"]]
                )

                local_attempts.append(
                    {
                        "session_id": None,
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
                    "_local_attempts": local_attempts,
                }
            )

    demo_users: list[tuple[str, str, str]] = []  # (archetype, name, email)
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

    for archetype, u_idx in hero_user_index_by_archetype.items():
        demo_users.append((archetype, identities[u_idx]["name"], identities[u_idx]["email"]))

    print("\nDemo users (one per behavioral pattern, for the Loom walkthrough):")
    for archetype, name, email in demo_users:
        print(f"  {archetype:>18}: {name} <{email}>")

    client.close()
    print("\nSeed complete.")


if __name__ == "__main__":
    asyncio.run(seed())
