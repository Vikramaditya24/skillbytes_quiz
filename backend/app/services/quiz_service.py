from datetime import datetime, timezone

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.config import settings
from app.repositories.catalog_repo import CatalogRepository
from app.repositories.quiz_repo import QuizRepository
from app.schemas.catalog import QuestionOption, QuestionPublicOut
from app.schemas.quiz import (
    CurrentQuestionOut,
    QuizResultOut,
    QuizSessionOut,
    SubmitAnswerResponse,
)


class QuizProgressionError(Exception):
    """Raised on out-of-order question access or answering a completed session."""


class QuizService:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.catalog = CatalogRepository(db)
        self.quiz_repo = QuizRepository(db)

    async def start_session(self, user_id: str, chapter_id: str) -> QuizSessionOut:
        chapter = await self.catalog.get_chapter(chapter_id)
        if chapter is None:
            raise ValueError(f"chapter {chapter_id} not found")

        available = await self.catalog.count_questions(chapter_id)
        sample_size = min(settings.quiz_session_size, available)
        if sample_size == 0:
            raise ValueError(f"chapter {chapter_id} has no questions")

        questions = await self.catalog.sample_questions(chapter_id, sample_size)

        now = datetime.now(timezone.utc)
        doc = {
            "user_id": user_id,
            "exam_id": chapter["exam_id"],
            "subject_id": chapter["subject_id"],
            "chapter_id": chapter_id,
            "question_ids": [q["id"] for q in questions],
            "current_index": 0,
            "status": "in_progress",
            "score": 0,
            "total_questions": sample_size,
            "started_at": now,
            "completed_at": None,
        }
        created = await self.quiz_repo.create_session(doc)
        return QuizSessionOut(**created)

    async def get_current_question(self, session_id: str) -> CurrentQuestionOut:
        session = await self.quiz_repo.get_session(session_id)
        if session is None:
            raise ValueError(f"session {session_id} not found")
        if session["status"] == "completed":
            raise QuizProgressionError("this quiz session is already completed")

        idx = session["current_index"]
        question_id = session["question_ids"][idx]
        questions_by_id = await self.catalog.get_questions_by_ids([question_id])
        q = questions_by_id[question_id]

        # Stamp shown_at server-side NOW, on the attempt-in-progress record.
        # We store it on the session so submit_answer can read it back -
        # tamper-resistant per Milestone 0 decision B4 (client can't fabricate it).
        await self.db.quiz_sessions.update_one(
            {"_id": ObjectId(session_id)},
            {"$set": {f"shown_at_by_index.{idx}": datetime.now(timezone.utc)}},
        )

        return CurrentQuestionOut(
            session_id=session_id,
            question_number=idx + 1,
            total_questions=session["total_questions"],
            question=QuestionPublicOut(
                id=q["id"],
                text=q["text"],
                options=[QuestionOption(**o) for o in q["options"]],
            ),
        )

    async def submit_answer(
        self, session_id: str, question_id: str, selected_option_key: str
    ) -> SubmitAnswerResponse:
        session = await self.quiz_repo.get_session(session_id)
        if session is None:
            raise ValueError(f"session {session_id} not found")
        if session["status"] == "completed":
            raise QuizProgressionError("this quiz session is already completed")

        idx = session["current_index"]
        expected_question_id = session["question_ids"][idx]
        if question_id != expected_question_id:
            # This is the server-side no-revisit / out-of-order enforcement:
            # the client cannot submit for any question other than the one
            # currently pointed to by current_index, regardless of what the
            # frontend's local state claims.
            raise QuizProgressionError(
                "question does not match the current position in this session "
                "(revisiting or skipping ahead is not allowed)"
            )

        questions_by_id = await self.catalog.get_questions_by_ids([question_id])
        question = questions_by_id[question_id]
        is_correct = selected_option_key == question["correct_option_key"]

        shown_at = session.get("shown_at_by_index", {}).get(str(idx)) or session["started_at"]
        answered_at = datetime.now(timezone.utc)
        duration_ms = int((answered_at - shown_at).total_seconds() * 1000)

        attempt_doc = {
            "session_id": session_id,
            "user_id": session["user_id"],
            "question_id": question_id,
            "exam_id": session["exam_id"],
            "subject_id": session["subject_id"],
            "chapter_id": session["chapter_id"],
            "question_sequence_number": idx + 1,
            "shown_at": shown_at,
            "answered_at": answered_at,
            "response_duration_ms": max(duration_ms, 0),
            "selected_option_key": selected_option_key,
            "is_correct": is_correct,
        }
        try:
            await self.quiz_repo.insert_attempt(attempt_doc)
        except ValueError as exc:
            # Unique (session_id, question_id) index tripped - a concurrent
            # duplicate submit for this same question lost the race. This is
            # a progression conflict, not a "not found" - surfaced as 409.
            raise QuizProgressionError(str(exc)) from exc

        updated = await self.quiz_repo.advance_session(
            session_id, expected_current_index=idx, score_increment=1 if is_correct else 0
        )
        if updated is None:
            # current_index changed between our read and write - a concurrent
            # duplicate submit lost the race. Treat as a progression error.
            raise QuizProgressionError("session progression conflict - please retry")

        next_number: int | None = idx + 2  # 1-based number of the *next* question
        if updated["current_index"] >= updated["total_questions"]:
            await self.quiz_repo.complete_session(session_id, answered_at)
            next_number = None
            status = "completed"
        else:
            status = "in_progress"

        return SubmitAnswerResponse(
            is_correct=is_correct,
            correct_option_key=question["correct_option_key"],
            session_status=status,
            next_question_number=next_number,
        )

    async def get_result(self, session_id: str) -> QuizResultOut:
        session = await self.quiz_repo.get_session(session_id)
        if session is None:
            raise ValueError(f"session {session_id} not found")
        if session["status"] != "completed":
            raise QuizProgressionError("quiz is not yet completed")

        total = session["total_questions"]
        score = session["score"]
        return QuizResultOut(
            session_id=session_id,
            score=score,
            total_questions=total,
            accuracy_pct=round(100 * score / total, 2) if total else 0.0,
            started_at=session["started_at"],
            completed_at=session["completed_at"],
        )
