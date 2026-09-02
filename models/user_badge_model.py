
import uuid
from typing import TYPE_CHECKING
from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from common.database import Base

if TYPE_CHECKING:
    from models.user_model import User
    from models.badge_model import Badge

class UserBadge(Base):
    __tablename__ = "UserBadge"

    user_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("user.id"), primary_key=True)
    badge_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("badge.id"), primary_key=True)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="badges")
    badge: Mapped["Badge"] = relationship("Badge", back_populates="users")

   