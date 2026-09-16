from pydantic import BaseModel, ConfigDict
from datetime import datetime
import uuid
from models.examination_model import ExaminationType, Type


class CreateExamination(BaseModel):
    user_id: uuid.UUID
    type: Type
    subjects: list[str]
    total_question: int | None = None
    total_score: int | None = None
    time: str | None = None
    total_questions_answered: int | None = 0
    total_questions_failed: int | None = 0
    questions_ids: list[int] | None = None
    correct_questions: list[str] | None = None
    failed_questions: list[str] | None = None
    exam_year: str
    exam_type: ExaminationType | str


class UpdateExamination(BaseModel):
    type: Type | str | None = None
    subjects: list[str] | None = None
    total_question: int | None = None
    total_score: int | None = None
    time: str | None = None
    total_questions_answered: int | None = None
    total_questions_failed: int | None = None
    questions_ids: list[int] | None = None
    correct_questions: list[str] | None = None
    failed_questions: list[str] | None = None
    exam_year: str | None = None
    exam_type: ExaminationType | str | None = None


class ExaminationReturn(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    type: Type | str
    subjects: list[str]
    total_question: int | None = None
    total_score: int | None = None
    time: str | None = None
    total_questions_answered: int
    total_questions_failed: int
    questions_ids: list[int] | None = None
    correct_questions: list[str] | None = None
    failed_questions: list[str] | None = None
    exam_year: str
    exam_type: ExaminationType | str
    created_at: datetime | None = None
    updated_at: datetime | None = None
    isDeleted: bool = False
