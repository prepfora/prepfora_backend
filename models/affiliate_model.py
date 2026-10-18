import uuid
from sqlalchemy import Boolean, String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column
from common.database import Base


class Affiliate(Base):
    __tablename__ = "affiliate"

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), default=uuid.uuid4, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    code: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    isSuspended: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)