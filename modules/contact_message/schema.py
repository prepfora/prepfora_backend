from uuid import UUID
from pydantic import ConfigDict
from pydantic_core.core_schema import model_field
from common.schema import CommonSchema
from pydantic import BaseModel, EmailStr

class CreateContactMessage(BaseModel):
    email: EmailStr
    first_name: str
    last_name: str
    message: str

class ContactMessageReturnType(CommonSchema):
    model_config=ConfigDict(from_attributes=True)

    id: UUID
    first_name: str
    last_name: str
    email: str