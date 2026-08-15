from datetime import datetime

from pydantic import BaseModel, Field


class LearningVelocityEntry(BaseModel):
    user_id: str
    user_name: str
    total_attempts: int
    accuracy_pct: float
    avg_response_time_ms: float
    consistency_score: float | None
    speed_score: float
    accuracy_score: float
    learning_velocity_index: float
    low_sample: bool


class LearningVelocityResponse(BaseModel):
    weights: dict[str, float]
    results: list[LearningVelocityEntry]


class FatigueWindow(BaseModel):
    window_index: int
    question_range: str  # e.g. "1-5"
    attempts: int
    accuracy_pct: float
    avg_response_time_ms: float
    accuracy_delta_pct: float  # vs window 0, in percentage points
    response_time_delta_pct: float  # vs window 0, relative %
    fatigue_flag: bool


class FatiguePoint(BaseModel):
    question_number: int
    accuracy_pct: float
    avg_response_time_ms: float
    accuracy_delta_pct: float
    response_time_delta_pct: float


class FatigueSessionEntry(BaseModel):
    session_id: str
    user_id: str
    user_name: str
    windows: list[FatigueWindow]
    question_progression: list[FatiguePoint] = Field(default_factory=list)
    overall_fatigue_flag: bool


class FatigueResponse(BaseModel):
    window_size: int
    disclaimer: str
    results: list[FatigueSessionEntry]


class DifficultyEntry(BaseModel):
    question_id: str
    question_text: str
    chapter_id: str
    total_attempts: int
    accuracy_pct: float
    avg_response_time_ms: float
    difficulty_score: float
    low_sample: bool


class DifficultyResponse(BaseModel):
    weights: dict[str, float]
    results: list[DifficultyEntry]


class RecentSessionSummary(BaseModel):
    session_id: str
    chapter_name: str
    score: int
    total_questions: int
    accuracy_pct: float
    completed_at: datetime | None


class PersonalProgressResponse(BaseModel):
    """
    "My Progress" - the logged-in learner's own numbers only. has_data=False
    means this user has no completed attempts yet (new/unused seed user) -
    the frontend renders an empty state rather than a broken chart.
    """

    has_data: bool
    learning_velocity: LearningVelocityEntry | None
    recent_sessions: list[RecentSessionSummary]
    latest_session_fatigue: FatigueSessionEntry | None
