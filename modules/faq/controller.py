from fastapi import APIRouter
from services.faq_service import get_faq as get_faq_service_method

router = APIRouter(
    prefix='/faq',
    tags=['faq'],
)

@router.get("")
def get_faq(page: int = 1, limit: int = 20):
    return get_faq_service_method(page, limit)