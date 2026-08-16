from fastapi import APIRouter, Depends, HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.api.deps import get_db
from app.repositories.user_repo import UserRepository
from app.schemas.analytics import (
    DifficultyResponse,
    FatigueResponse,
    LearningVelocityResponse,
    PersonalProgressResponse,
)
from app.services.analytics_service import AnalyticsService

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/learning-velocity", response_model=LearningVelocityResponse)
async def learning_velocity(db: AsyncIOMotorDatabase = Depends(get_db)):
    """Cohort-wide LVI ranking across all learners"""
    return await AnalyticsService(db).learning_velocity()


@router.get("/fatigue", response_model=FatigueResponse)
async def fatigue(db: AsyncIOMotorDatabase = Depends(get_db)):
    """Cohort-wide, session-by-session fatigue view across all learners."""
    return await AnalyticsService(db).fatigue_analysis()


@router.get("/question-difficulty", response_model=DifficultyResponse)
async def question_difficulty(db: AsyncIOMotorDatabase = Depends(get_db)):
    return await AnalyticsService(db).question_difficulty()


@router.get("/my-progress/{user_id}", response_model=PersonalProgressResponse)
async def my_progress(user_id: str, db: AsyncIOMotorDatabase = Depends(get_db)):
    """
    The logged-in learner's own numbers only - same formulas as the cohort
    endpoints above, scoped via $match on user_id. This is what "My Progress"
    reads; it never returns another learner's data.
    """
    user = await UserRepository(db).get_user(user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="user not found")
    return await AnalyticsService(db).my_progress(user_id)
