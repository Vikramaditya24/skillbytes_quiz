from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from app.core.config import settings

_client: AsyncIOMotorClient | None = None


def get_client() -> AsyncIOMotorClient:
    global _client
    if _client is None:
        _client = AsyncIOMotorClient(settings.mongo_uri, tz_aware=True)
    return _client


def get_database() -> AsyncIOMotorDatabase:
    """FastAPI dependency: single injected AsyncIOMotorClient, one DB handle reused everywhere."""
    return get_client()[settings.mongo_db_name]


async def close_client() -> None:
    global _client
    if _client is not None:
        _client.close()
        _client = None


async def create_indexes(db: AsyncIOMotorDatabase) -> None:
    """
    Index set matches Milestone 0 Section D exactly. No speculative indexes on
    exams/subjects/chapters/users - these are small, fully-scanned lookup tables.
    """
    await db.questions.create_index("chapter_id")

    await db.quiz_sessions.create_index([("user_id", 1), ("status", 1)])

    await db.question_attempts.create_index(
        [("session_id", 1), ("question_id", 1)], unique=True
    )
    await db.question_attempts.create_index(
        [("user_id", 1), ("session_id", 1), ("question_sequence_number", 1)]
    )
    await db.question_attempts.create_index("question_id")
