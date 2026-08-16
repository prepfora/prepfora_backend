import uuid
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from common.database import Base


class Waitlist(Base):
    __tablename__ = "waitlist"
    
    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), default=uuid.uuid4, primary_key=True, index=True)
    first_name: Mapped[str] = mapped_column("first_name", String(50), nullable=False)
    last_name: Mapped[str] = mapped_column("last_name", String(50), nullable=False)
    email: Mapped[str] = mapped_column("email", String(100), nullable=False, unique=True)
    phone_number: Mapped[str] = mapped_column("phone_number", String(15), nullable=True)
    
    