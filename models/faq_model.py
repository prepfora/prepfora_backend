import uuid
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from common.database import Base

class Faq(Base):
    __tablename__ = "faq"

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), default=uuid.uuid4, primary_key=True, index=True)
    title: Mapped[str] = mapped_column("title", String(255), nullable=False)
    description: Mapped[str] = mapped_column(String, nullable=False)