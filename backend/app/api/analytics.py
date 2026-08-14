from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.api.deps import get_db
from app.schemas.analytics import DifficultyResponse, FatigueResponse, LearningVelocityResponse
from app.services.analytics_service import AnalyticsService

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/learning-velocity", response_model=LearningVelocityResponse)
async def learning_velocity(db: AsyncIOMotorDatabase = Depends(get_db)):
    return await AnalyticsService(db).learning_velocity()


@router.get("/fatigue", response_model=FatigueResponse)
async def fatigue(db: AsyncIOMotorDatabase = Depends(get_db)):
    return await AnalyticsService(db).fatigue_analysis()


@router.get("/question-difficulty", response_model=DifficultyResponse)
async def question_difficulty(db: AsyncIOMotorDatabase = Depends(get_db)):
    return await AnalyticsService(db).question_difficulty()
