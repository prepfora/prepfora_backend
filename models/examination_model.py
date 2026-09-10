from sqlalchemy import String, Integer
from sqlalchemy.dialects.postgresql import ARRAY, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column
from common.database import Base
import uuid
from enum import Enum


class ExaminationType(str, Enum):
    WAEC = "waec"
    UTME = "utme"
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
    time: Mapped[str | None] = mapped_column(String(50), nullable=True)
    total_questions_answered: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_questions_failed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    questions_ids: Mapped[list[int] | None] = mapped_column(ARRAY(Integer), nullable=True)
    correct_questions: Mapped[list[str] | None] = mapped_column(ARRAY(String), nullable=True)
    failed_questions: Mapped[list[str] | None] = mapped_column(ARRAY(String), nullable=True)
    exam_year: Mapped[str] = mapped_column(String(50), nullable=False)
    exam_type: Mapped[str] = mapped_column(String(50), nullable=False)
