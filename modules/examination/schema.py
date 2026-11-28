from pydantic import BaseModel, ConfigDict, Field, AliasChoices, model_validator, field_validator, computed_field
from datetime import datetime
import uuid
import json
from models.examination_model import ExaminationType, Type
from modules.questions.schema import QuestionItem
from modules.badges.schema import BadgeResponse


class CreateExamination(BaseModel):
    user_id: uuid.UUID
    type: Type
    subjects: list[str]
    total_question: int | None = None
    total_score: int | None = None
    score: float | None = None
    time: str | None = None
    total_questions_answered: int | None = 0
    total_questions_failed: int | None = 0
    questions_ids: list[int] | None = Field(
        default=None,
        validation_alias=AliasChoices("questions_ids", "question_ids"),
    )
    correct_questions: list[str] | None = None
    failed_questions: list[str] | None = None
    exam_year: str
    exam_type: ExaminationType | str


class UpdateExamination(BaseModel):
    type: Type | str | None = None
    subjects: list[str] | None = None
    total_question: int | None = None
    total_score: int | None = None
    score: float | None = None
    time: str | None = None
    total_questions_answered: int | None = None
    total_questions_failed: int | None = None
    questions_ids: list[int] | None = Field(
        default=None,
        validation_alias=AliasChoices("questions_ids", "question_ids"),
    )
    correct_questions: list[str] | None = None
    failed_questions: list[str] | None = None
    exam_year: str | None = None
    exam_type: ExaminationType | str | None = None


class AnswerReturn(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    examination_id: uuid.UUID
    user_id: uuid.UUID
    question_id: int
    picked_answer: str | None = None
    correct_answer: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    isDeleted: bool = False

    @computed_field
    @property
    def is_correct(self) -> bool:
        if self.picked_answer is not None and self.correct_answer is not None:
            return self.picked_answer.strip().lower() == self.correct_answer.strip().lower()
        return False


class ExaminationReturn(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: uuid.UUID
    user_id: uuid.UUID
    type: Type | str
    subjects: list[str]
    total_question: int | None = None
    total_score: int | None = None
    score: float | None = None
    time: str | None = None
    total_questions_answered: int
    total_questions_failed: int
    questions_ids: list[int] | None = None
    question_ids: list[int] | None = None
    questions: list[QuestionItem] | None = None
    correct_questions: list[str] | None = None
    failed_questions: list[str] | None = None
    exam_year: str
    exam_type: ExaminationType | str
    is_completed: bool = False
    completed_at: datetime | None = None
    answers: list[AnswerReturn] = Field(default_factory=list)
    created_at: datetime | None = None
    updated_at: datetime | None = None
    isDeleted: bool = False

    @field_validator("questions_ids", "question_ids", "subjects", "correct_questions", "failed_questions", mode="before")
    @classmethod
    def parse_array_field(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except Exception:
                return [v]
        if isinstance(v, list) and v and isinstance(v[0], str) and v[0] == "[" and v[-1] == "]":
            try:
                return json.loads("".join(v))
            except Exception:
                pass
        return v

    @model_validator(mode="after")
    def sync_question_ids(self) -> "ExaminationReturn":
        if self.question_ids is None and self.questions_ids is not None:
            self.question_ids = self.questions_ids
        elif self.questions_ids is None and self.question_ids is not None:
            self.questions_ids = self.question_ids
        return self


class SubmitAnswer(BaseModel):
    question_id: int
    picked_answer: str
    correct_answer: str | None = None
    user_id: uuid.UUID | None = None


class CreateAnswer(BaseModel):
    examination_id: uuid.UUID
    question_id: int
    picked_answer: str
    correct_answer: str | None = None
    user_id: uuid.UUID | None = None


class SubjectScoreBreakdown(BaseModel):
    subject: str
    is_english: bool
    correct_answers: int
    total_questions_for_formula: int
    multiplier: float
    score: float


class JambScoreResponse(BaseModel):
    examination_id: uuid.UUID
    exam_type: str
    score: float
    max_score: float = 400.0
    total_correct_answers: int
    subject_breakdown: list[SubjectScoreBreakdown] = Field(default_factory=list)
    newly_earned_badges: list[BadgeResponse] = Field(default_factory=list)


class EndExaminationResponse(BaseModel):
    examination: ExaminationReturn
    score: float
    is_jamb: bool
    subject_breakdown: list[SubjectScoreBreakdown] | None = None
    newly_earned_badges: list[BadgeResponse] = Field(default_factory=list)


class ExaminationSubjectPerformance(BaseModel):
    subject: str
    total_questions: int
    answered: int
    correct: int
    failed: int
    unanswered: int
    accuracy_percentage: float
    score_percentage: float
    jamb_score: float | None = None


class ExaminationPerformanceResponse(BaseModel):
    examination_id: uuid.UUID
    user_id: uuid.UUID
    exam_type: str
    exam_year: str
    type: str
    is_completed: bool
    total_questions: int
    total_answered: int
    total_correct: int
    total_failed: int
    total_unanswered: int
    overall_accuracy_percentage: float
    overall_score_percentage: float
    score: float | None = None
    subjects: list[ExaminationSubjectPerformance] = Field(default_factory=list)

