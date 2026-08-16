from pydantic import field_validator
from pydantic import EmailStr
from uuid import UUID
from pydantic import ConfigDict
from pydantic import BaseModel
from common.schema import CommonSchema

class CreateWaitListEntry(BaseModel):
    email: str
    first_name: str
    last_name: str
    phone_number: str

    @field_validator("email", mode="before")
    @classmethod
    def validate_email(cls, v: str) -> str:
        if not v or "@" not in v:
            raise ValueError("Please provide a valid email address.")
        return v.lower()


class WaitListReturnType(CommonSchema):
    model_config=ConfigDict(from_attributes=True)

    id: UUID
    first_name: str
    last_name: str
    phone_number: str
    email: EmailStr

    

    