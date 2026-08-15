from motor.motor_asyncio import AsyncIOMotorDatabase

from app.repositories.base import serialize, to_object_id


class CatalogRepository:
    """
    Trivial CRUD/lookups only - deliberately no service layer in front of these.
    Routes queries directly to repository for one-line, stateless lookups.
    """

    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db

    async def list_exams(self) -> list[dict]:
        cursor = self.db.exams.find().sort("name", 1)
        return [serialize(d) async for d in cursor]

    async def list_subjects(self, exam_id: str) -> list[dict]:
        cursor = self.db.subjects.find({"exam_id": exam_id}).sort("name", 1)
        return [serialize(d) async for d in cursor]

    async def list_chapters(self, subject_id: str) -> list[dict]:
        cursor = self.db.chapters.find({"subject_id": subject_id}).sort("name", 1)
        return [serialize(d) async for d in cursor]

    async def get_chapter(self, chapter_id: str) -> dict | None:
        doc = await self.db.chapters.find_one({"_id": to_object_id(chapter_id)})
        return serialize(doc)

    async def sample_questions(self, chapter_id: str, sample_size: int) -> list[dict]:
        """
        Random sample of `sample_size` questions from a chapter's pool via
        $sample - server-side random selection, no full-table pull into Python.
        """
        pipeline = [
            {"$match": {"chapter_id": chapter_id}},
            {"$sample": {"size": sample_size}},
        ]
        cursor = self.db.questions.aggregate(pipeline)
        return [serialize(d) async for d in cursor]

    async def get_questions_by_ids(self, ids: list[str]) -> dict[str, dict]:
        oids = [to_object_id(i) for i in ids]
        cursor = self.db.questions.find({"_id": {"$in": oids}})
        docs = [serialize(d) async for d in cursor]
        return {d["id"]: d for d in docs}

    async def count_questions(self, chapter_id: str) -> int:
        return await self.db.questions.count_documents({"chapter_id": chapter_id})
