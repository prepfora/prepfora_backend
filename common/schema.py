from datetime import datetime
from pydantic import BaseModel


class CommonSchema(BaseModel):
    created_at: datetime | None
    updated_at: datetime | None
    isDeleted: bool | None
    deleted_at: datetime | None
    