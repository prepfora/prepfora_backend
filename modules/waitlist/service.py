
from common.classes.return_type import Pagination
from sqlalchemy import func
from fastapi import param_functions
from common.logger import logger
from common.exceptions.bad_request_exception import BadRequestException
from modules.waitlist.schema import CreateWaitListEntry
from sqlalchemy import select
from modules.waitlist.schema import WaitListReturnType
from common.classes.return_type import ReturnType
from common.database import get_db
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from models.waitlist_model import Waitlist
from common.exceptions.internal_server_exception import InternalServerException


class WaitlistService:
    db: AsyncSession

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_wait_list_entry(self, payload: CreateWaitListEntry) -> ReturnType[WaitListReturnType]:
        try:
            stmt = select(Waitlist).where(Waitlist.email == payload.email.lower())
            result = await self.db.execute(stmt)
            check = result.scalars().first()
            logger.error("CHECK VALUE")
            logger.error(str(check))
            if  check is not None:
                raise BadRequestException("User already exists in waitlist")
            entry = Waitlist(
                email=payload.email.lower(),
                first_name=payload.first_name,
                last_name=payload.last_name,
            )
            self.db.add(entry)
            await self.db.commit()
            await self.db.refresh(entry)
            ### TODO - Implement email sending with resend
            return ReturnType[WaitListReturnType](
                success=True,
                message="Waitlist entry created successfully",
                data=WaitListReturnType(
                    email=entry.email,
                    first_name=entry.first_name,
                    last_name=entry.last_name,
                    id=entry.id,
                    created_at=entry.created_at,
                    updated_at=entry.updated_at,
                    isDeleted=entry.isDeleted,
                    deleted_at=entry.deleted_at
                )
            )
        except Exception as e:
            logger.error(str(e))
            raise InternalServerException(str(e))

    async def get_waitlist_entries(self, page: int = 1, limit: int = 20) -> ReturnType[list[WaitListReturnType]]:
        try:
            if page < 1:
                logger.error("Page must be greater then 0")
                raise BadRequestException("Page must be greater than 0")
            if limit < 1:
                logger.error("Limit must be greater than 0")
                raise BadRequestException("Limit must be greater than 0")
            logger.info("Fetching waitlist entries")
            count_stmt = select(func.count()).select_from(Waitlist).where(Waitlist.isDeleted == False)
            total_result = await self.db.execute(count_stmt)
            total = total_result.scalar_one()
            stmt = (
                select(Waitlist)
                .where(Waitlist.isDeleted == False)
                .offset((page - 1) * limit)
                .limit(limit)
            )
            result = await self.db.execute(stmt)
            entries = list(result.scalars().all())
            logger.info("Waitlist entries fetched successfully")
            return ReturnType[list[WaitListReturnType]](
                success=True,
                message="Waitlist entries fetched successfully",
                data=entries,
                pagination=Pagination(
                    total=total,
                    page=page,
                    per_page=limit,
                )
            )
        except Exception as e:
            logger.error("Error fetching waitlist entries: " + str(e))
            raise InternalServerException(str(e))
            
        

### WAITLIST DEPENDENCY
def get_waitlist_service(
    db: AsyncSession = Depends(get_db),
) -> WaitlistService:
    return WaitlistService(db)