from datetime import datetime
from typing import TYPE_CHECKING
from sqlalchemy import String, Integer, Float, Boolean, DateTime
from sqlalchemy.dialects.postgresql import ARRAY, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from common.database import Base
import uuid
from enum import Enum

if TYPE_CHECKING:
    from models.answer_model import Answer


class ExaminationType(str, Enum):
    WAEC = "waec"
    UTME = "utme"
    JAMB = "jamb"
    NECO = "neco"
    POST_UTME = "post-utme"

class Type(str, Enum):
    PRACTISE = "practice"
    MOCK = "mock"


class Examination(Base):
    __tablename__ = "user_examination"

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), default=uuid.uuid4, primary_key=True, index=True)
    type: Mapped[Type] = mapped_column(String(50), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    subjects: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False)
    total_question: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    score: Mapped[float | None] = mapped_column(Float, nullable=True, default=0.0)
    time: Mapped[str | None] = mapped_column(String(50), nullable=True)

    total_questions_answered: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_questions_failed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    questions_ids: Mapped[list[int] | None] = mapped_column(ARRAY(Integer), nullable=True)
    correct_questions: Mapped[list[str] | None] = mapped_column(ARRAY(String), nullable=True)
    failed_questions: Mapped[list[str] | None] = mapped_column(ARRAY(String), nullable=True)
    exam_year: Mapped[str] = mapped_column(String(50), nullable=False)
    exam_type: Mapped[str] = mapped_column(String(50), nullable=False)
    is_completed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    answers: Mapped[list["Answer"]] = relationship(
        "Answer",
        back_populates="examination",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    @property
    def question_ids(self) -> list[int] | None:
        return self.questions_ids

    @question_ids.setter
    def question_ids(self, val: list[int] | None) -> None:
        self.questions_ids = val

