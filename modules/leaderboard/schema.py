import uuid
from datetime import datetime
from pydantic import BaseModel, Field


class LeaderboardEntry(BaseModel):
    rank: int
    user_id: uuid.UUID
    first_name: str | None = None
    last_name: str | None = None
    profile_picture: str | None = None
    university: str | None = None
    state: str | None = None
    exam_type: str
    best_score: float
    average_score: float
    total_exams: int
    prep_points: int = 0
    last_exam_at: datetime | None = None


class LeaderboardResponse(BaseModel):
    exam_type: str
    type: str | None = None
    entries: list[LeaderboardEntry] = Field(default_factory=list)
    current_user: LeaderboardEntry | None = None
