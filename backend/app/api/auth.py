from fastapi import APIRouter, Depends, HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.api.deps import get_db
from app.repositories.user_repo import UserRepository
from app.schemas.user import LoginRequest, LoginResponse, UserOut

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/users", response_model=list[UserOut])
async def list_users(db: AsyncIOMotorDatabase = Depends(get_db)):
    """Populates the login screen's user picker."""
    return await UserRepository(db).list_users()


@router.post("/login", response_model=LoginResponse)
async def login(payload: LoginRequest, db: AsyncIOMotorDatabase = Depends(get_db)):
    """
    Dummy auth per assignment spec: select a predefined user, no password.
    session_token is just the user_id - deliberately not a JWT (see README).
    """
    user = await UserRepository(db).get_user(payload.user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="user not found")
    return LoginResponse(user=UserOut(**user), session_token=user["id"])
