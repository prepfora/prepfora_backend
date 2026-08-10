from uuid import UUID
from modules.faq.schema import Update_Faq
from modules.faq.schema import Faq_Return
from modules.faq.schema import Create_Faq
from common.classes.return_type import ReturnType
from common.database import get_db
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import APIRouter

from common.exceptions.bad_request_exception import BadRequestException
from modules.faq.faq_service import get_faq_service, FaqService

router = APIRouter(
    prefix='/faq',
    tags=['faq'],
)

@router.post("", response_model=ReturnType[Faq_Return], status_code=201)
async def create_faq(faq: Create_Faq, service: FaqService = Depends(get_faq_service)):
    try:
        return await service.create_faq(faq)
    except Exception as e:
        raise BadRequestException(str(e))


@router.get("", response_model=ReturnType[list[Faq_Return]])
async def get_faq(page: int = 1, limit: int = 20, service: FaqService = Depends(get_faq_service)):
    try:
        return await service.get_faq(page, limit)
    except Exception as e:
        raise BadRequestException(str(e))

@router.put("/{id}", response_model=ReturnType[Faq_Return])
async def update_faq(faq: Update_Faq, id: UUID, service: FaqService = Depends(get_faq_service)):
    try:
        return await service.update_faq(faq, id)
    except Exception as e:
        raise BadRequestException(str(e))

@router.delete("/{id}", response_model=ReturnType[Faq_Return])
async def delete_faq(id: UUID, service: FaqService = Depends(get_faq_service)):
    try:
        return await service.delete_faq(id)
    except Exception as e:
        raise BadRequestException(str(e))