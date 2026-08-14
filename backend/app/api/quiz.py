from fastapi import APIRouter, Depends, HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.api.deps import get_db
from app.schemas.quiz import (
    CurrentQuestionOut,
    QuizResultOut,
    QuizSessionOut,
    StartQuizRequest,
    SubmitAnswerRequest,
    SubmitAnswerResponse,
)
from app.services.quiz_service import QuizProgressionError, QuizService

router = APIRouter(tags=["quiz"])


@router.post("/chapters/{chapter_id}/quiz-sessions", response_model=QuizSessionOut)
async def start_quiz(
    chapter_id: str, payload: StartQuizRequest, db: AsyncIOMotorDatabase = Depends(get_db)
):
    try:
        return await QuizService(db).start_session(payload.user_id, chapter_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/quiz-sessions/{session_id}/current-question", response_model=CurrentQuestionOut)
async def current_question(session_id: str, db: AsyncIOMotorDatabase = Depends(get_db)):
    try:
        return await QuizService(db).get_current_question(session_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except QuizProgressionError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/quiz-sessions/{session_id}/answer", response_model=SubmitAnswerResponse)
async def submit_answer(
    session_id: str, payload: SubmitAnswerRequest, db: AsyncIOMotorDatabase = Depends(get_db)
):
    try:
        return await QuizService(db).submit_answer(
            session_id, payload.question_id, payload.selected_option_key
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except QuizProgressionError as exc:
        # 409 Conflict: revisit attempt, duplicate submit, or answering after completion.
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/quiz-sessions/{session_id}/result", response_model=QuizResultOut)
async def get_result(session_id: str, db: AsyncIOMotorDatabase = Depends(get_db)):
    try:
        return await QuizService(db).get_result(session_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except QuizProgressionError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
