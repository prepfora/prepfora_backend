from fastapi import APIRouter, Depends, Query
from modules.universities.service import get_universities_service, UniversitiesService
from modules.universities.schema import UniversitiesListResponse
from common.classes.return_type import ReturnType
from common.exceptions.bad_request_exception import BadRequestException
from common.logger import logger

router = APIRouter(
    prefix="/universities",
    tags=["Universities"],
)


@router.get("", response_model=ReturnType[UniversitiesListResponse], status_code=200)
async def get_universities(
    name: str | None = Query(None, description="Search by university name"),
    state: str | None = Query(None, description="Filter by state"),
    search: str | None = Query(None, description="General search term across name, state, city, and abbreviation"),
    service: UniversitiesService = Depends(get_universities_service)
) -> ReturnType[UniversitiesListResponse]:
    try:
        return await service.get_universities(name=name, state=state, search=search)
    except Exception as e:
        logger.error("Failed to get universities: " + str(e))
        raise BadRequestException("Failed to get universities: " + str(e))
