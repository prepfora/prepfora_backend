from datetime import datetime
import uuid
from pydantic import BaseModel, Field, AliasChoices
from models.user_model import Examination


class UserBadgeResponse(BaseModel):
    id: uuid.UUID
    title: str
    description: str
    image: str
    points_required: int
    is_active: bool

    class Config:
        from_attributes = True


class UserListItemResponse(BaseModel):
    id: uuid.UUID
    first_name: str | None = None
    last_name: str | None = None
    email: str
    phone: str | None = None
    state: str | None = None
    university: str | None = None
    examinations: list[Examination] | None = None
    current_expectation: str | None = None
    current_examination_date: str | None = None
    prep_points: int | None = 0
    best_score: int | None = 0
    profile_picture: str | None = None
    referral_code: str | None = None
    total_exams: int = 0
    created_at: datetime | None = None
    updated_at: datetime | None = None

    class Config:
        from_attributes = True


class UserDetailResponse(BaseModel):
    id: uuid.UUID
    first_name: str | None = None
    last_name: str | None = None
    email: str
    phone: str | None = None
    state: str | None = None
    university: str | None = None
    examinations: list[Examination] | None = None
    current_expectation: str | None = None
    current_examination_date: str | None = None
    prep_points: int | None = 0
    best_score: int | None = 0
    profile_picture: str | None = None
    referral_code: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    # Performance and activity statistics
    total_exams: int = 0
    total_mock_exams: int = 0
    total_practice_exams: int = 0
    total_badges: int = 0
    badges: list[UserBadgeResponse] = []

    class Config:
        from_attributes = True
