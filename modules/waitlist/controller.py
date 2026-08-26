from modules.waitlist.schema import WaitListReturnType
from common.classes.return_type import ReturnType
from common.exceptions.bad_request_exception import BadRequestException
from common.logger import logger
from modules.waitlist.service import get_waitlist_service
from fastapi import Depends
from modules.waitlist.service import WaitlistService
from modules.waitlist.schema import CreateWaitListEntry
from fastapi import APIRouter
from modules.waitlist.schema import SendWaitlistEmailPayload

router = APIRouter(
    prefix='/waitlist',
    tags=['waitlist'],
)


@router.post("", response_model=ReturnType[WaitListReturnType], status_code=201)
async def create_waitlist(body: CreateWaitListEntry, service: WaitlistService = Depends(get_waitlist_service)):
    try:
        return await service.create_wait_list_entry(body)
    except Exception as e:
        logger.fatal("Failed to create waitlist entry: " + str(e))
        raise BadRequestException("Failed to create waitlist entry " + str(e))



@router.get("", response_model=ReturnType[list[WaitListReturnType]], status_code=200)
async def get_waitlist(service: WaitlistService = Depends(get_waitlist_service), page: int = 1, limit: int = 20):
    try:
        return await service.get_waitlist_entries(page, limit)
    except Exception as e:
        logger.error("Failed to get waitlist entries: " + str(e))
        raise BadRequestException("Failed to get waitlist entries")

@router.post("/send_message", response_model=ReturnType[str], status_code=200)
async def send_email(payload: SendWaitlistEmailPayload, service: WaitlistService = Depends(get_waitlist_service)):
    try:
         await service.send_email_to_users(payload.emails, payload.message, payload.subject)
         return ReturnType[str](data="Email sent successfully")
    except Exception as e:
        logger.error("Failed to send email: " + str(e))
        raise BadRequestException("Failed to send email")

@router.get("/total", response_model=ReturnType[int], status_code=200)
async def get_total_waitlist_entries(service: WaitlistService = Depends(get_waitlist_service)):
    try:
        return await service.get_total_waitlist_entries()
    except Exception as e:
        logger.error("Failed to get total waitlist entries: " + str(e))
        raise BadRequestException("Failed to get total waitlist entries")
    
        