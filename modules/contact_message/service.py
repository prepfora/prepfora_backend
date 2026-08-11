from common.database import get_db
from fastapi import Depends
from common.classes.return_type import Pagination
from sqlalchemy import func
from sqlalchemy import select
from common.exceptions.bad_request_exception import BadRequestException
from asyncio import selector_events
from common.exceptions.internal_server_exception import InternalServerException
from models.contact_message import ContactMessage
from modules.contact_message.schema import CreateContactMessage
from common.classes.return_type import ReturnType
from sqlalchemy.ext.asyncio import AsyncSession
from modules.contact_message.schema import ContactMessageReturnType
from common.logger import logger


class ContactMessageService:
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create_message(self, payload: CreateContactMessage) -> ReturnType[ContactMessageReturnType]:
        try:
            logger.info("Creating contact message")
            message = ContactMessage(
                first_name=payload.first_name,
                last_name=payload.last_name,
                email=payload.email,
                message=payload.message
            )
            self.db.add(message)
            await self.db.commit()
            await self.db.refresh(message)
            return ReturnType[ContactMessageReturnType](
                success=True,
                message="Message created successfully",
                data=ContactMessageReturnType(
                    id=message.id,
                    first_name=message.first_name,
                    last_name=message.last_name,
                    email=message.email,
                    message=message.message,
                    created_at=message.created_at,
                    updated_at=message.updated_at,
                    isDeleted=message.isDeleted,
                    deleted_at=message.deleted_at
                )
            )
            
        except Exception as e:
            logger.error("Error creating contact message: " + str(e))
            raise InternalServerException(str(e))
        
    async def get_message(self, page: int = 1, limit: int = 20) -> ReturnType[list[ContactMessageReturnType]]:
            try:
                if page < 1:
                    logger.error("Page must be greater then 0")
                    raise BadRequestException("Page must be greater than 0")
                if limit < 1:
                    logger.error("Limit must be greater than 0")
                    raise BadRequestException("Limit must be greater than 0")
                logger.info("Fetching contact messages")
                count_stmt = select(func.count()).select_from(ContactMessage).where(ContactMessage.isDeleted == False)
                total_result = await self.db.execute(count_stmt)
                total = total_result.scalar_one()
                stmt = (
                    select(ContactMessage)
                    .where(ContactMessage.isDeleted == False)
                    .offset((page - 1) * limit)
                    .limit(limit)
                )
                result = await self.db.execute(stmt)
                entries = list(result.scalars().all())
                logger.info("Contact messages fetched successfully")
                return ReturnType[list[ContactMessageReturnType]](
                    success=True,
                    message="Contact messages fetched successfully",
                    data=entries,
                    pagination=Pagination(
                        total=total,
                        page=page,
                        per_page=limit,
                    )
                )
            except Exception as e:
                logger.error("Error fetching contact messages: " + str(e))
                raise InternalServerException(str(e))
            

def get_contact_message_service(
    db: AsyncSession = Depends(get_db),
) -> ContactMessageService:
    return ContactMessageService(db)