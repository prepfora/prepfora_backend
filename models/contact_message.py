from sqlalchemy import Text
import uuid
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from common.database import Base


class ContactMessage(Base):
    __tablename__ = "contact_message"
    
    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), default=uuid.uuid4, primary_key=True, index=True)
    first_name: Mapped[str] = mapped_column("first_name", String(50), nullable=False)
    last_name: Mapped[str] = mapped_column("last_name", String(50), nullable=False)
    email: Mapped[str] = mapped_column("email", String(100), nullable=False, unique=True)
    message: Mapped[str] = mapped_column("message", Text, nullable=False)
    
    