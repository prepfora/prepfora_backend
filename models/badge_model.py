from sqlalchemy.orm import relationship
from models.user_badge_model import UserBadge
from sqlalchemy import Boolean
from common.database import Base
import uuid
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.types import String, Enum, Integer

class Badge(Base):
    __tablename__ = "badge"

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), default=uuid.uuid4, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    description: Mapped[str] = mapped_column(String, nullable=False)
    image: Mapped[str] = mapped_column(String(255), nullable=False)
    points_required: Mapped[int] = mapped_column(Integer, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Relationships
    users: Mapped[list[UserBadge]] = relationship("UserBadge", back_populates="badge")
    