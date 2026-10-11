from pydantic import BaseModel, ConfigDict, Field, AliasChoices
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
    model_config = ConfigDict(populate_by_name=True, from_attributes=True)

    id: int | str
    subject: str | None = None
    question: str
    option: QuestionOption | dict[str, Any] | None = None
    section: str | None = ""
    image: str | None = ""
    answer: str | None = ""
    solution: str | None = ""
    examtype: ExamType | str | None = ""
    examyear: str | None = ""
    hasPassage: int | bool | None = None
    has_passage: bool | None = None
    category: str | None = None


class QuestionsByIdsRequest(BaseModel):
    ids: list[int] = Field(
        default_factory=list,
        validation_alias=AliasChoices("ids", "question_ids", "questions_ids"),
        description="Array of question IDs to fetch",
    )


class QuestionSingleResponse(BaseModel):
    subject: str | None = None
    status: int | None = 200
    data: QuestionItem


class QuestionMultipleResponse(BaseModel):
    subject: str | None = None
    status: int | None = 200
    data: list[QuestionItem]


class CreateCustomQuestion(BaseModel):
    subject: str | None = None
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
    subject: str | None = None
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
    subject: str | None = None
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






