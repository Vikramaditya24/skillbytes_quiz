from datetime import datetime

from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError

from app.repositories.base import serialize, to_object_id


class QuizRepository:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db

    async def create_session(self, doc: dict) -> dict:
        result = await self.db.quiz_sessions.insert_one(doc)
        return await self.get_session(str(result.inserted_id))

    async def get_session(self, session_id: str) -> dict | None:
        doc = await self.db.quiz_sessions.find_one({"_id": to_object_id(session_id)})
        return serialize(doc)

    async def advance_session(
        self, session_id: str, expected_current_index: int, score_increment: int
    ) -> dict | None:
        """
        Atomic, server-enforced progression: only advances current_index if it
        still matches `expected_current_index` at write time. This is what
        actually prevents answering the same question twice or the client
        racing two submits - not just an app-level "if" check beforehand.
        """
        new_index = expected_current_index + 1
        result = await self.db.quiz_sessions.find_one_and_update(
            {"_id": to_object_id(session_id), "current_index": expected_current_index},
            {"$inc": {"score": score_increment}, "$set": {"current_index": new_index}},
            return_document=ReturnDocument.AFTER,
        )
        return serialize(result)

    async def complete_session(self, session_id: str, completed_at: datetime) -> dict | None:
        result = await self.db.quiz_sessions.find_one_and_update(
            {"_id": to_object_id(session_id)},
            {"$set": {"status": "completed", "completed_at": completed_at}},
            return_document=ReturnDocument.AFTER,
        )
        return serialize(result)

    async def insert_attempt(self, doc: dict) -> dict:
        """
        Relies on the unique (session_id, question_id) index (see core/db.py)
        as the real backstop against duplicate submits - this is a defense in
        depth layer, not the only guard (see advance_session above).
        """
        try:
            result = await self.db.question_attempts.insert_one(doc)
        except DuplicateKeyError as exc:
            raise ValueError("this question has already been answered in this session") from exc
        doc = dict(doc)
        doc["id"] = str(result.inserted_id)
        return doc
