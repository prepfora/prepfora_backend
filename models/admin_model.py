from models.faq_model import PG_UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Boolean
from common.database import Base
import uuid

class Admin(Base):
    __tablename__ = "admin"

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), default=uuid.uuid4, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    role_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    profile_picture: Mapped[str|None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    