from pydantic import BaseModel, ConfigDict, field_validator

from app.schemas.common import PyObjectId


class ExamOut(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    id: PyObjectId = ""
    name: str
    description: str


class SubjectOut(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    id: PyObjectId = ""
    exam_id: str
    name: str


class ChapterOut(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    id: PyObjectId = ""
    subject_id: str
    exam_id: str
    name: str


class QuestionOption(BaseModel):
    key: str
    text: str


class QuestionCreate(BaseModel):
    """Used only by the seed script - validates shape at the boundary per spec requirement."""

    chapter_id: str
    subject_id: str
    exam_id: str
    text: str
    options: list[QuestionOption]
    correct_option_key: str

    @field_validator("options")
    @classmethod
    def exactly_four_options(cls, v: list[QuestionOption]) -> list[QuestionOption]:
        if len(v) != 4:
            raise ValueError("a question must have exactly 4 options")
        keys = {o.key for o in v}
        if len(keys) != 4:
            raise ValueError("option keys must be unique")
        return v

    @field_validator("correct_option_key")
    @classmethod
    def correct_key_must_exist(cls, v: str, info) -> str:
        options = info.data.get("options")
        if options and v not in {o.key for o in options}:
            raise ValueError("correct_option_key must match one of the option keys")
        return v


class QuestionPublicOut(BaseModel):
    """
    What the frontend sees while a quiz is in progress: NO correct_option_key.
    Leaking the answer client-side would defeat the "don't rely on frontend
    state" instruction just as badly as skipping server-side revisit checks.
    """

    model_config = ConfigDict(populate_by_name=True)
    id: PyObjectId = ""
    text: str
    options: list[QuestionOption]
