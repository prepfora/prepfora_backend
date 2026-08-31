from typing import TYPE_CHECKING
from sqlalchemy.orm import relationship, Mapped, mapped_column
from common.database import Base
import uuid
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.types import String

if TYPE_CHECKING:
    from models.user_model import User

class Activity(Base):
    __tablename__ = "activity"

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), default=uuid.uuid4, primary_key=True, index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(String, nullable=False)

    # relationship
    user: Mapped["User"] = relationship("User", back_populates="activities")
