from datetime import datetime, timedelta, timezone

import pytest

from app.services.analytics_service import AnalyticsService
from tests.test_analytics_aggregation import attempt

pytestmark = pytest.mark.asyncio


class TestMyProgressScoping:
    async def test_new_user_with_no_attempts_has_no_data(self, db):
        base = datetime.now(timezone.utc)
        u = await db.users.insert_one({"name": "New User", "email": "n@x.com", "created_at": base})

        result = await AnalyticsService(db).my_progress(str(u.inserted_id))
        assert result.has_data is False
        assert result.learning_velocity is None
        assert result.recent_sessions == []

    async def test_my_progress_only_reflects_this_users_attempts(self, db):
        base = datetime.now(timezone.utc)
        u1 = await db.users.insert_one({"name": "Learner One", "email": "l1@x.com", "created_at": base})
        u2 = await db.users.insert_one({"name": "Learner Two", "email": "l2@x.com", "created_at": base})
        uid1, uid2 = str(u1.inserted_id), str(u2.inserted_id)

        attempts = []
        for seq in range(1, 6):
            attempts.append(attempt("s1", uid1, f"q{seq}", "ch1", seq, 2000, True, base))
        for seq in range(1, 6):
            attempts.append(attempt("s2", uid2, f"q{seq}", "ch1", seq, 9000, False, base))
        await db.question_attempts.insert_many(attempts)

        progress1 = await AnalyticsService(db).my_progress(uid1)
        assert progress1.has_data is True
        assert progress1.learning_velocity.user_id == uid1
        assert progress1.learning_velocity.accuracy_pct == 100.0

        progress2 = await AnalyticsService(db).my_progress(uid2)
        assert progress2.has_data is True
        assert progress2.learning_velocity.user_id == uid2
        assert progress2.learning_velocity.accuracy_pct == 0.0

        # cross-check: user1's progress must not contain any of user2's numbers
        assert progress1.learning_velocity.accuracy_pct != progress2.learning_velocity.accuracy_pct

    async def test_recent_sessions_scoped_to_user_and_chapter_named(self, db):
        base = datetime.now(timezone.utc)
        u = await db.users.insert_one({"name": "Learner", "email": "l@x.com", "created_at": base})
        uid = str(u.inserted_id)

        chapter = await db.chapters.insert_one({"subject_id": "s1", "exam_id": "e1", "name": "Algebra - Chapter 1"})
        chapter_id = str(chapter.inserted_id)

        await db.quiz_sessions.insert_one(
            {
                "user_id": uid,
                "exam_id": "e1",
                "subject_id": "s1",
                "chapter_id": chapter_id,
                "question_ids": ["q1", "q2"],
                "current_index": 2,
                "status": "completed",
                "score": 2,
                "total_questions": 2,
                "started_at": base - timedelta(minutes=5),
                "completed_at": base,
            }
        )
        # An in_progress session for the same user should NOT appear in recent_sessions.
        await db.quiz_sessions.insert_one(
            {
                "user_id": uid,
                "exam_id": "e1",
                "subject_id": "s1",
                "chapter_id": chapter_id,
                "question_ids": ["q1", "q2"],
                "current_index": 0,
                "status": "in_progress",
                "score": 0,
                "total_questions": 2,
                "started_at": base,
                "completed_at": None,
            }
        )

        result = await AnalyticsService(db).my_progress(uid)
        assert len(result.recent_sessions) == 1
        assert result.recent_sessions[0].chapter_name == "Algebra - Chapter 1"
        assert result.recent_sessions[0].score == 2
