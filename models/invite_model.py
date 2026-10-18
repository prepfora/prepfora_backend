import uuid
from datetime import datetime
from sqlalchemy import Boolean, DateTime, String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column
from common.database import Base


class Invite(Base):
    __tablename__ = "invite"

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), default=uuid.uuid4, primary_key=True, index=True)
    code: Mapped[str] = mapped_column(String(6), nullable=False, unique=True, index=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    isActive: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    endDate: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)