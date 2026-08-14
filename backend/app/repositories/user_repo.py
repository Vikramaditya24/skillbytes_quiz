from motor.motor_asyncio import AsyncIOMotorDatabase

from app.repositories.base import serialize, to_object_id


class UserRepository:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db

    async def list_users(self) -> list[dict]:
        cursor = self.db.users.find().sort("name", 1)
        return [serialize(d) async for d in cursor]

    async def get_user(self, user_id: str) -> dict | None:
        doc = await self.db.users.find_one({"_id": to_object_id(user_id)})
        return serialize(doc)
