from typing import TYPE_CHECKING
from sqlalchemy.orm import relationship
import uuid
from enum import Enum
from common.database import Base
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, ARRAY
from sqlalchemy.types import String, Enum as SQLEnum, Integer

if TYPE_CHECKING:
    from models.user_badge_model import UserBadge
    from models.activity_model import Activity

class Examination(str, Enum):
    waec = "waec"
    neco = "neco"
    utme = "utme"
    jamb = "jamb"

class User(Base):
    __tablename__ = "user"

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), default=uuid.uuid4, primary_key=True, index=True)
    first_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    last_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    state: Mapped[str | None] = mapped_column(String(255), nullable=True)
    university: Mapped[str | None] = mapped_column(String(255), nullable=True)
    examinations: Mapped[list[Examination] | None] = mapped_column(ARRAY(SQLEnum(Examination)), nullable=True)
    current_expectation: Mapped[str | None] = mapped_column(String(255), nullable=True)
    prep_points: Mapped[int | None] = mapped_column(Integer, nullable=True, default=0)
    best_score: Mapped[int | None] = mapped_column(Integer, nullable=True, default=0)

    # 2. Relationship
    activities: Mapped[list["Activity"]] = relationship("Activity", back_populates="user", cascade="all, delete-orphan")
    badges: Mapped[list["UserBadge"]] = relationship("UserBadge", back_populates="user", cascade="all, delete-orphan")
