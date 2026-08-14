from pydantic import BaseModel


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


class FatigueSessionEntry(BaseModel):
    session_id: str
    user_id: str
    user_name: str
    windows: list[FatigueWindow]
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
