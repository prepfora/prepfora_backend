from datetime import datetime

from sqlalchemy import DateTime, func, Boolean
from sqlalchemy.orm import Mapped, mapped_column

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from common.config import settings


engine = create_async_engine(
    settings.database_url,
    echo=True,
    pool_pre_ping=True,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    updated_at:  Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    isDeleted: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
    )
    deleted_at:  Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        server_default=None,
        default=None
    )
    pass


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session