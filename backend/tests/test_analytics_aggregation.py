"""
Deterministic fixtures with known expected rankings/values - per the
"test behavior and expected values, not merely HTTP status codes" instruction.
Uses the MongoDB aggregation pipelines directly (not mocked math), so these
also validate the pipeline shape actually returned by mongomock's engine.
"""

from datetime import datetime, timedelta, timezone

import pytest

from app.services.analytics_service import AnalyticsService

pytestmark = pytest.mark.asyncio


def attempt(
    session_id, user_id, question_id, chapter_id, seq, duration_ms, is_correct, base_time
):
    shown = base_time + timedelta(seconds=seq * 10)
    return {
        "session_id": session_id,
        "user_id": user_id,
        "question_id": question_id,
        "exam_id": "exam1",
        "subject_id": "subj1",
        "chapter_id": chapter_id,
        "question_sequence_number": seq,
        "shown_at": shown,
        "answered_at": shown + timedelta(milliseconds=duration_ms),
        "response_duration_ms": duration_ms,
        "selected_option_key": "A" if is_correct else "B",
        "is_correct": is_correct,
    }


class TestLearningVelocityIndex:
    async def test_perfect_fast_consistent_learner_ranks_first(self, db):
        base = datetime.now(timezone.utc)

        # "Perfect learner": all correct, fast, identical times -> should rank #1
        u1 = await db.users.insert_one({"name": "Perfect Learner", "email": "p@x.com",
                                          "created_at": base})
        # "Weak learner": all wrong, slow, highly variable times -> should rank last
        u2 = await db.users.insert_one({"name": "Weak Learner", "email": "w@x.com",
                                          "created_at": base})

        attempts = []
        for seq in range(1, 6):
            attempts.append(
                attempt("s1", str(u1.inserted_id), f"q{seq}", "ch1", seq, 2000, True, base)
            )
        # weak learner: wrong answers, slow AND variable durations
        durations = [8000, 15000, 6000, 20000, 9000]
        for seq, dur in zip(range(1, 6), durations):
            attempts.append(
                attempt("s2", str(u2.inserted_id), f"q{seq}", "ch1", seq, dur, False, base)
            )
        await db.question_attempts.insert_many(attempts)

        result = await AnalyticsService(db).learning_velocity()
        assert result.results[0].user_id == str(u1.inserted_id)
        assert result.results[0].accuracy_pct == 100.0
        assert result.results[-1].user_id == str(u2.inserted_id)
        assert result.results[-1].accuracy_pct == 0.0
        # perfect learner's LVI must strictly exceed the weak learner's
        assert result.results[0].learning_velocity_index > result.results[-1].learning_velocity_index

    async def test_single_attempt_user_flagged_low_sample_with_null_consistency(self, db):
        base = datetime.now(timezone.utc)
        u = await db.users.insert_one({"name": "Solo", "email": "s@x.com", "created_at": base})
        await db.question_attempts.insert_one(
            attempt("s1", str(u.inserted_id), "q1", "ch1", 1, 3000, True, base)
        )

        result = await AnalyticsService(db).learning_velocity()
        entry = result.results[0]
        assert entry.consistency_score is None
        assert entry.low_sample is True
        # LVI must still be computed (using the neutral consistency default)
        assert entry.learning_velocity_index > 0


class TestFatigueAnalysis:
    async def test_declining_performance_sets_fatigue_flag(self, db):
        base = datetime.now(timezone.utc)
        u = await db.users.insert_one({"name": "Tired", "email": "t@x.com", "created_at": base})
        uid = str(u.inserted_id)

        attempts = []
        # window 0 (seq 1-5): fast, all correct
        for seq in range(1, 6):
            attempts.append(attempt("s1", uid, f"q{seq}", "ch1", seq, 2000, True, base))
        # window 1 (seq 6-10): much slower, mostly wrong -> should trip fatigue_flag
        for seq in range(6, 11):
            attempts.append(attempt("s1", uid, f"q{seq}", "ch1", seq, 6000, False, base))
        await db.question_attempts.insert_many(attempts)

        result = await AnalyticsService(db).fatigue_analysis()
        session = result.results[0]
        assert len(session.windows) == 2
        assert session.windows[0].fatigue_flag is False  # baseline window is never flagged
        assert session.windows[1].accuracy_pct == 0.0
        assert session.windows[1].fatigue_flag is True
        assert session.overall_fatigue_flag is True

    async def test_stable_performance_does_not_flag(self, db):
        base = datetime.now(timezone.utc)
        u = await db.users.insert_one({"name": "Steady", "email": "st@x.com", "created_at": base})
        uid = str(u.inserted_id)

        attempts = []
        for seq in range(1, 11):
            attempts.append(attempt("s2", uid, f"q{seq}", "ch1", seq, 3000, True, base))
        await db.question_attempts.insert_many(attempts)

        result = await AnalyticsService(db).fatigue_analysis()
        session = result.results[0]
        assert session.overall_fatigue_flag is False

    async def test_question_progression_has_one_point_per_question_in_order(self, db):
        """
        `question_progression` (FatiguePoint list) is the per-question detail
        behind the coarser 5-question windows - My Progress charts this
        directly. Each point's accuracy is 0 or 100 (a single question is
        either right or wrong), in ascending question_number order, and its
        deltas are measured against the same window-0 baseline as the
        window-level view.
        """
        base = datetime.now(timezone.utc)
        u = await db.users.insert_one({"name": "Prog", "email": "prog@x.com", "created_at": base})
        uid = str(u.inserted_id)

        attempts = []
        # window 0 (seq 1-5): all correct, fast
        for seq in range(1, 6):
            attempts.append(attempt("s3", uid, f"q{seq}", "ch1", seq, 2000, True, base))
        # window 1 (seq 6-7): incorrect, slower
        for seq in range(6, 8):
            attempts.append(attempt("s3", uid, f"q{seq}", "ch1", seq, 6000, False, base))
        await db.question_attempts.insert_many(attempts)

        result = await AnalyticsService(db).fatigue_analysis()
        session = result.results[0]

        progression = session.question_progression
        assert len(progression) == 7
        assert [p.question_number for p in progression] == list(range(1, 8))
        # first five questions were all correct -> 100% each
        assert all(p.accuracy_pct == 100.0 for p in progression[:5])
        # last two were wrong -> 0% each
        assert all(p.accuracy_pct == 0.0 for p in progression[5:])
        # the wrong/slow questions must show a negative accuracy delta and a
        # positive time delta vs the window-0 baseline, matching the window view
        assert progression[5].accuracy_delta_pct < 0
        assert progression[5].response_time_delta_pct > 0


class TestQuestionDifficulty:
    async def test_hard_question_ranks_above_easy_question(self, db):
        base = datetime.now(timezone.utc)
        u = await db.users.insert_one({"name": "U", "email": "u@x.com", "created_at": base})
        uid = str(u.inserted_id)

        attempts = []
        # "hard" question: low accuracy, long response time
        for seq in range(1, 6):
            attempts.append(
                attempt(f"s{seq}", uid, "hard_q", "ch1", 1, 12000, seq == 1, base)
            )
        # "easy" question: high accuracy, short response time
        for seq in range(1, 6):
            attempts.append(
                attempt(f"s{seq+10}", uid, "easy_q", "ch1", 1, 2000, seq != 1, base)
            )
        await db.question_attempts.insert_many(attempts)

        result = await AnalyticsService(db).question_difficulty()
        by_id = {e.question_id: e for e in result.results}
        assert by_id["hard_q"].difficulty_score > by_id["easy_q"].difficulty_score
        assert result.results[0].question_id == "hard_q"  # ranked hardest-first

    async def test_low_attempt_count_is_flagged(self, db):
        base = datetime.now(timezone.utc)
        u = await db.users.insert_one({"name": "U", "email": "u2@x.com", "created_at": base})
        uid = str(u.inserted_id)
        await db.question_attempts.insert_one(
            attempt("s1", uid, "rare_q", "ch1", 1, 3000, True, base)
        )

        result = await AnalyticsService(db).question_difficulty()
        assert result.results[0].low_sample is True