"""
These construct a quiz_session directly (bypassing the $sample-based
start_session flow, which needs a real MongoDB - mongomock's aggregation
support for $sample is limited) so the progression/no-revisit/duplicate/
ownership logic in QuizService can be exercised against a deterministic,
known question order.
"""

from datetime import datetime, timezone

import pytest
from bson import ObjectId

from app.services.quiz_service import OwnershipError, QuizProgressionError, QuizService

pytestmark = pytest.mark.asyncio

OWNER = "u1"
OTHER_USER = "u2"


async def seed_minimal_catalog(db):
    exam = await db.exams.insert_one({"name": "Exam", "description": "d"})
    subject = await db.subjects.insert_one({"exam_id": str(exam.inserted_id), "name": "Subj"})
    chapter = await db.chapters.insert_one(
        {"subject_id": str(subject.inserted_id), "exam_id": str(exam.inserted_id), "name": "Ch1"}
    )
    question_ids = []
    for i in range(3):
        q = await db.questions.insert_one(
            {
                "chapter_id": str(chapter.inserted_id),
                "subject_id": str(subject.inserted_id),
                "exam_id": str(exam.inserted_id),
                "text": f"Q{i}",
                "options": [{"key": k, "text": k} for k in "ABCD"],
                "correct_option_key": "A",
            }
        )
        question_ids.append(str(q.inserted_id))
    return {
        "exam_id": str(exam.inserted_id),
        "subject_id": str(subject.inserted_id),
        "chapter_id": str(chapter.inserted_id),
        "question_ids": question_ids,
    }


async def seed_session(db, catalog, user_id=OWNER):
    doc = {
        "user_id": user_id,
        "exam_id": catalog["exam_id"],
        "subject_id": catalog["subject_id"],
        "chapter_id": catalog["chapter_id"],
        "question_ids": catalog["question_ids"],
        "current_index": 0,
        "status": "in_progress",
        "score": 0,
        "total_questions": len(catalog["question_ids"]),
        "started_at": datetime.now(timezone.utc),
        "completed_at": None,
    }
    result = await db.quiz_sessions.insert_one(doc)
    return str(result.inserted_id)


class TestQuizProgression:
    async def test_serves_questions_in_fixed_order(self, db):
        catalog = await seed_minimal_catalog(db)
        session_id = await seed_session(db, catalog)
        service = QuizService(db)

        cq = await service.get_current_question(session_id, OWNER)
        assert cq.question_number == 1
        assert cq.question.id == catalog["question_ids"][0]

    async def test_correct_answer_increments_score_and_advances(self, db):
        catalog = await seed_minimal_catalog(db)
        session_id = await seed_session(db, catalog)
        service = QuizService(db)

        await service.get_current_question(session_id, OWNER)
        resp = await service.submit_answer(session_id, OWNER, catalog["question_ids"][0], "A")
        assert resp.is_correct is True
        assert resp.session_status == "in_progress"
        assert resp.next_question_number == 2

        session = await db.quiz_sessions.find_one({"_id": ObjectId(session_id)})
        assert session["score"] == 1
        assert session["current_index"] == 1

    async def test_incorrect_answer_does_not_increment_score(self, db):
        catalog = await seed_minimal_catalog(db)
        session_id = await seed_session(db, catalog)
        service = QuizService(db)

        await service.get_current_question(session_id, OWNER)
        resp = await service.submit_answer(session_id, OWNER, catalog["question_ids"][0], "B")
        assert resp.is_correct is False

        session = await db.quiz_sessions.find_one({"_id": ObjectId(session_id)})
        assert session["score"] == 0

    async def test_cannot_answer_a_question_out_of_current_position(self, db):
        """Server-enforced no-revisit: submitting for question[1] while
        current_index still points at question[0] must be rejected."""
        catalog = await seed_minimal_catalog(db)
        session_id = await seed_session(db, catalog)
        service = QuizService(db)

        await service.get_current_question(session_id, OWNER)
        with pytest.raises(QuizProgressionError):
            await service.submit_answer(session_id, OWNER, catalog["question_ids"][1], "A")

    async def test_cannot_resubmit_the_same_question_twice(self, db):
        """After answering question[0], current_index moves to 1 - resubmitting
        question[0] must be rejected as out-of-position, not silently accepted."""
        catalog = await seed_minimal_catalog(db)
        session_id = await seed_session(db, catalog)
        service = QuizService(db)

        await service.get_current_question(session_id, OWNER)
        await service.submit_answer(session_id, OWNER, catalog["question_ids"][0], "A")

        with pytest.raises(QuizProgressionError):
            await service.submit_answer(session_id, OWNER, catalog["question_ids"][0], "A")

    async def test_completes_session_after_last_question_and_blocks_further_answers(self, db):
        catalog = await seed_minimal_catalog(db)
        session_id = await seed_session(db, catalog)
        service = QuizService(db)

        resp = None
        for qid in catalog["question_ids"]:
            await service.get_current_question(session_id, OWNER)
            resp = await service.submit_answer(session_id, OWNER, qid, "A")

        assert resp.session_status == "completed"
        assert resp.next_question_number is None

        with pytest.raises(QuizProgressionError):
            await service.get_current_question(session_id, OWNER)

        result = await service.get_result(session_id, OWNER)
        assert result.total_questions == 3
        assert result.score == 3
        assert result.accuracy_pct == 100.0

    async def test_result_unavailable_before_completion(self, db):
        catalog = await seed_minimal_catalog(db)
        session_id = await seed_session(db, catalog)
        service = QuizService(db)

        with pytest.raises(QuizProgressionError):
            await service.get_result(session_id, OWNER)


class TestSessionOwnership:
    """A user must not be able to access or act on another learner's session
    by supplying a different user_id, even if they know/guess the session_id."""

    async def test_other_user_cannot_view_current_question(self, db):
        catalog = await seed_minimal_catalog(db)
        session_id = await seed_session(db, catalog, user_id=OWNER)
        service = QuizService(db)

        with pytest.raises(OwnershipError):
            await service.get_current_question(session_id, OTHER_USER)

    async def test_other_user_cannot_submit_answer(self, db):
        catalog = await seed_minimal_catalog(db)
        session_id = await seed_session(db, catalog, user_id=OWNER)
        service = QuizService(db)
        await service.get_current_question(session_id, OWNER)

        with pytest.raises(OwnershipError):
            await service.submit_answer(session_id, OTHER_USER, catalog["question_ids"][0], "A")

        # confirm the owner's session was NOT advanced by the rejected attempt
        session = await db.quiz_sessions.find_one({"_id": ObjectId(session_id)})
        assert session["current_index"] == 0
        assert session["score"] == 0

    async def test_other_user_cannot_view_result(self, db):
        catalog = await seed_minimal_catalog(db)
        session_id = await seed_session(db, catalog, user_id=OWNER)
        service = QuizService(db)
        for qid in catalog["question_ids"]:
            await service.get_current_question(session_id, OWNER)
            await service.submit_answer(session_id, OWNER, qid, "A")

        with pytest.raises(OwnershipError):
            await service.get_result(session_id, OTHER_USER)

    async def test_owner_is_unaffected_by_ownership_check(self, db):
        """Sanity check: the ownership check doesn't accidentally block the
        legitimate owner."""
        catalog = await seed_minimal_catalog(db)
        session_id = await seed_session(db, catalog, user_id=OWNER)
        service = QuizService(db)

        cq = await service.get_current_question(session_id, OWNER)
        assert cq.session_id == session_id


class TestShownAtIdempotency:
    """Regression test: calling current-question repeatedly for the same
    question must not reset shown_at, or response_duration_ms would be
    silently corrupted by page refreshes / retried requests."""

    async def test_repeated_current_question_calls_do_not_reset_shown_at(self, db):
        catalog = await seed_minimal_catalog(db)
        session_id = await seed_session(db, catalog)
        service = QuizService(db)

        await service.get_current_question(session_id, OWNER)
        session_after_first = await db.quiz_sessions.find_one({"_id": ObjectId(session_id)})
        first_shown_at = session_after_first["shown_at_by_index"]["0"]

        # Simulate a page refresh / retried request - call it again before answering.
        await service.get_current_question(session_id, OWNER)
        await service.get_current_question(session_id, OWNER)
        session_after_repeats = await db.quiz_sessions.find_one({"_id": ObjectId(session_id)})
        second_shown_at = session_after_repeats["shown_at_by_index"]["0"]

        assert first_shown_at == second_shown_at

    async def test_response_duration_reflects_first_shown_at_not_latest_call(self, db):
        """End-to-end: even after multiple current-question calls, the
        eventual attempt's response_duration_ms is measured from the FIRST
        time the question was shown, not the most recent poll."""
        catalog = await seed_minimal_catalog(db)
        session_id = await seed_session(db, catalog)
        service = QuizService(db)

        await service.get_current_question(session_id, OWNER)
        session = await db.quiz_sessions.find_one({"_id": ObjectId(session_id)})
        original_shown_at = session["shown_at_by_index"]["0"]

        # Poll again several times (simulating refreshes) - should not move shown_at.
        for _ in range(3):
            await service.get_current_question(session_id, OWNER)

        await service.submit_answer(session_id, OWNER, catalog["question_ids"][0], "A")
        attempt = await db.question_attempts.find_one({"session_id": session_id})
        assert attempt["shown_at"] == original_shown_at
