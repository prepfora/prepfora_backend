import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class CreateBadge(BaseModel):
    code: str | None = None
    title: str
    description: str
    image: str = ""
    points_required: int = 0
    is_active: bool = True


class UpdateBadge(BaseModel):
    code: str | None = None
    title: str | None = None
    description: str | None = None
    image: str | None = None
    points_required: int | None = None
    is_active: bool | None = None


class BadgeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    code: str | None = None
    title: str
    description: str
    image: str
    points_required: int
    is_active: bool
    created_at: datetime | None = None
    updated_at: datetime | None = None


class UserBadgeDetailResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    badge: BadgeResponse
    earned_at: datetime | None = None
