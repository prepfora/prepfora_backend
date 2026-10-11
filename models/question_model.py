from sqlalchemy import Integer, String, JSON, Boolean, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from common.database import Base


class Question(Base):
    __tablename__ = "question"
    __table_args__ = (
        UniqueConstraint("subject", "external_id", name="uq_question_subject_external_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, index=True)
    external_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    subject: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
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
