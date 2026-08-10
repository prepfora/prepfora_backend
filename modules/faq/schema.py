from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, ConfigDict, EmailStr

class Create_Faq(BaseModel):
    title: str
    description: str


class Faq_Return(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    description: str
    created_at: datetime
    updated_at: datetime
    isDeleted: bool
    deleted_at: datetime | None

class Update_Faq(BaseModel):
    title: str | None
    description: str | None