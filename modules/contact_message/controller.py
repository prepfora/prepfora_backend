from fastapi import APIRouter, Depends, HTTPException
from modules.contact_message.service import get_contact_message_service, ContactMessageService
from modules.contact_message.schema import CreateContactMessage, ContactMessageReturnType
from common.classes.return_type import ReturnType

router = APIRouter(
    prefix="/contact_message",
    tags=["Contact Message"],
    responses={404: {"description": "Not found"}},
)

@router.post("/create", response_model=ReturnType[ContactMessageReturnType], status_code=201)
async def create_message(
    payload: CreateContactMessage,
    service: ContactMessageService = Depends(get_contact_message_service)
) -> ReturnType[ContactMessageReturnType]:
    return await service.create_message(payload)


@router.get("/", response_model=ReturnType[list[ContactMessageReturnType]], status_code=200)
async def get_message(
    page: int = 1,
    limit: int = 20,
    service: ContactMessageService = Depends(get_contact_message_service)
) -> ReturnType[list[ContactMessageReturnType]]:
    return await service.get_message(page, limit)

    