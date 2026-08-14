from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.api.deps import get_db
from app.repositories.catalog_repo import CatalogRepository
from app.schemas.catalog import ChapterOut, ExamOut, SubjectOut

router = APIRouter(tags=["catalog"])


@router.get("/exams", response_model=list[ExamOut])
async def list_exams(db: AsyncIOMotorDatabase = Depends(get_db)):
    return await CatalogRepository(db).list_exams()


@router.get("/exams/{exam_id}/subjects", response_model=list[SubjectOut])
async def list_subjects(exam_id: str, db: AsyncIOMotorDatabase = Depends(get_db)):
    return await CatalogRepository(db).list_subjects(exam_id)


@router.get("/subjects/{subject_id}/chapters", response_model=list[ChapterOut])
async def list_chapters(subject_id: str, db: AsyncIOMotorDatabase = Depends(get_db)):
    return await CatalogRepository(db).list_chapters(subject_id)
