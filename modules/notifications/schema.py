from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict


class NotificationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    body: str
    is_read: bool
    user_id: UUID | None = None
    is_for_admin: bool = False
    read_by: list[str] = []
    created_at: datetime | None = None
    updated_at: datetime | None = None


class CreateNotificationRequest(BaseModel):
    title: str
    body: str
    user_id: UUID | None = None
    is_for_admin: bool = False
