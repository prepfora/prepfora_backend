from pydantic import BaseModel, ConfigDict
from typing import Any, Literal
from datetime import datetime
import uuid
from models.examination_model import ExaminationType, Type

ExamType = Literal["waec", "utme", "neco", "post-utme"]


class QuestionOption(BaseModel):
    a: str | None = None
    b: str | None = None
    c: str | None = None
    d: str | None = None
    e: str | None = None


class QuestionItem(BaseModel):
    id: int | str
    question: str
    option: QuestionOption | dict[str, Any] | None = None
    section: str | None = ""
    image: str | None = ""
    answer: str | None = ""
    solution: str | None = ""
    examtype: ExamType | str | None = ""
    examyear: str | None = ""
    hasPassage: int | bool | None = None
    category: str | None = None


class QuestionSingleResponse(BaseModel):
    subject: str | None = None
    status: int | None = 200
    data: QuestionItem


class QuestionMultipleResponse(BaseModel):
    subject: str | None = None
    status: int | None = 200
    data: list[QuestionItem]


class CreateCustomQuestion(BaseModel):
    question: str
    option: QuestionOption | dict[str, Any] | None = None
    section: str | None = None
    image: str | None = None
    answer: str | None = None
    solution: str | None = None
    examtype: ExamType | None = None
    examyear: str | None = None
    has_passage: bool | None = None
    category: str | None = None


class UpdateCustomQuestion(BaseModel):
    question: str | None = None
    option: QuestionOption | dict[str, Any] | None = None
    section: str | None = None
    image: str | None = None
    answer: str | None = None
    solution: str | None = None
    examtype: ExamType | None = None
    examyear: str | None = None
    has_passage: bool | None = None
    category: str | None = None


class CustomQuestionReturn(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    question: str
    option: QuestionOption | dict[str, Any] | None = None
    section: str | None = None
    image: str | None = None
    answer: str | None = None
    solution: str | None = None
    examtype: ExamType | str | None = None
    examyear: str | None = None
    has_passage: bool | None = None
    category: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    isDeleted: bool = False


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


