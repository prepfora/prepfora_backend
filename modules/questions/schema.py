from pydantic import BaseModel, ConfigDict
from typing import Any, Literal
from datetime import datetime

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
