from pydantic import BaseModel
from typing import Any


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
    examtype: str | None = ""
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
