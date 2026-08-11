from typing import Generic, TypeVar
from pydantic import BaseModel

T = TypeVar("T")

class Pagination(BaseModel):
    total: int
    page: int
    per_page: int


class ReturnType(BaseModel, Generic[T]):
    success: bool = True
    message: str = "Operation successful"
    data: T | None = None
    pagination: Pagination | None = None