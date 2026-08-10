from sqlalchemy.dialects.postgresql import ARRAY
from models.admin_model import PG_UUID
from common.database import Base
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Boolean
import uuid
from enum import StrEnum

class Permission(StrEnum):
    OVERVIEW = 'overview'
    USERS = 'users'
    ADMINS = 'admins'
    QUESTION = 'question'

class Admin_Role(Base):
    __tablename__ = 'admin_role'

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), default=uuid.uuid4, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    permissions: Mapped[list[Permission]] = mapped_column(ARRAY(String), nullable=False, default=[Permission.OVERVIEW])
