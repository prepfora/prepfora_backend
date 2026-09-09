from sqlalchemy import Integer, String, JSON, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from common.database import Base


class Question(Base):
    __tablename__ = "question"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, index=True)
    question: Mapped[str] = mapped_column(String, nullable=False)
    option: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    section: Mapped[str | None] = mapped_column(String, nullable=True)
    image: Mapped[str | None] = mapped_column(String(255), nullable=True)
    answer: Mapped[str | None] = mapped_column(String, nullable=True)
    solution: Mapped[str | None] = mapped_column(String, nullable=True)
    examtype: Mapped[str | None] = mapped_column(String(50), nullable=True)
    examyear: Mapped[str | None] = mapped_column(String(50), nullable=True)
    has_passage: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)
