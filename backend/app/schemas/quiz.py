from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

from app.schemas.common import PyObjectId
from app.schemas.catalog import QuestionPublicOut

SessionStatus = Literal["in_progress", "completed"]


class StartQuizRequest(BaseModel):
    user_id: str


class QuizSessionOut(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    id: PyObjectId = ""
    user_id: str
    exam_id: str
    subject_id: str
    chapter_id: str
    total_questions: int
    current_index: int
    status: SessionStatus
    score: int
    started_at: datetime
    completed_at: datetime | None = None


class CurrentQuestionOut(BaseModel):
    session_id: str
    question_number: int  # 1-based, human-facing
    total_questions: int
    question: QuestionPublicOut


class SubmitAnswerRequest(BaseModel):
    """
    Submit an answer to the current question. Note: shown_at is server-side
    only and is not accepted in this request. The server uses the timestamp
    it stamped when serving the question (per README Assumptions #4) to
    calculate response_duration_ms.
    """
    user_id: str
    question_id: str
    selected_option_key: str


class SubmitAnswerResponse(BaseModel):
    is_correct: bool
    correct_option_key: str
    session_status: SessionStatus
    next_question_number: int | None  # None once the session is completed


class QuizResultOut(BaseModel):
    session_id: str
    score: int
    total_questions: int
    accuracy_pct: float
    started_at: datetime
    completed_at: datetime | None
