from uuid import UUID
from modules.faq.schema import Update_Faq
from modules.faq.schema import Create_Faq
from modules.faq.schema import Faq_Return
from common.database import get_db
from fastapi import Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from models.faq_model import Faq
from common.logger import logger

from common.classes.return_type import ReturnType, Pagination
from common.exceptions.bad_request_exception import BadRequestException

class FaqService:
    db: AsyncSession

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_faq(self, page: int = 1, limit: int = 20) -> ReturnType[list[Faq_Return]]:
        if page < 1:
            logger.error("Page must be greater then 0")
            raise BadRequestException("Page must be greater than 0")
        if limit < 1:
            logger.error("Limit must be greater than 0")
            raise BadRequestException("Limit must be greater than 0")

        count_stmt = select(func.count()).select_from(Faq).where(Faq.isDeleted == False)
        total_result = await self.db.execute(count_stmt)
        total = total_result.scalar_one()

        stmt = (
            select(Faq)
            .where(Faq.isDeleted == False)
            .offset((page - 1) * limit)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        faqs = list(result.scalars().all())
        logger.info("Faqs returned successfully")
        return ReturnType(
            success=True,
            message="Faqs returned successfully",
            data=faqs,
            pagination=Pagination(
                total=total,
                page=page,
                per_page=limit,
            ),
        )

    async def create_faq(self, body: Create_Faq) -> ReturnType[Faq_Return]:
        faq = Faq(
            title=body.title,
            description=body.description,
        )
        self.db.add(faq)
        await self.db.commit()
        await self.db.refresh(faq)
        logger.info("Faq created successfully")
        return ReturnType(
            success=True,
            message="Faq created",
            data=faq,
        )

    async def update_faq(self, body: Update_Faq, id: UUID) -> ReturnType[Faq_Return]:
        stmt = select(Faq).where(Faq.id == id, Faq.isDeleted == False)
        result = await self.db.execute(stmt)
        faq = result.scalars().first()
        if not faq:
            logger.error("Faq not found with id: " + str(id))
            raise BadRequestException("Faq not found")
        faq.title = body.title or faq.title
        faq.description = body.description or faq.description
        await self.db.commit()
        await self.db.refresh(faq)
        logger.info("Faq updated successfully")
        return ReturnType(
            success=True,
            message="Faq updated",
            data=faq,
        )

    async def delete_faq(self, id: UUID) -> ReturnType[Faq_Return]:
        stmt = select(Faq).where(Faq.id == id, Faq.isDeleted == False)
        result = await self.db.execute(stmt)
        faq = result.scalars().first()
        if not faq:
            logger.error("Faq not found with id: " + str(id))
            raise BadRequestException("Faq not found")
        faq.isDeleted = True
        await self.db.commit()
        await self.db.refresh(faq)
        logger.info("Faq deleted successfully")
        return ReturnType(
            success=True,
            message="Faq deleted",
            data=faq,
        )


def get_faq_service(
    db: AsyncSession = Depends(get_db),
) -> FaqService:
    return FaqService(db)