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
    first_name: Mapped[str] = mapped_column(String(255), nullable=False)
    last_name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    state: Mapped[str] = mapped_column(String(255), nullable=False)
    university: Mapped[str] = mapped_column(String(255), nullable=False)
    examinations: Mapped[list[Examination]] = mapped_column(ARRAY(SQLEnum(Examination)), nullable=False)
    current_expectation: Mapped[str] = mapped_column(String(255), nullable=False)
    prep_points: Mapped[int] = mapped_column(Integer, default=0)
    best_score: Mapped[int] = mapped_column(Integer, default=0)

    # 2. Relationship
    activities: Mapped[list["Activity"]] = relationship("Activity", back_populates="user", cascade="all, delete-orphan")
    badges: Mapped[list["UserBadge"]] = relationship("UserBadge", back_populates="user", cascade="all, delete-orphan")
