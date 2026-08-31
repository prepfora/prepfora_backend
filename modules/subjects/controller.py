from fastapi import APIRouter, Depends, Query
from common.classes.return_type import ReturnType
from common.exceptions.bad_request_exception import BadRequestException
from common.logger import logger
from modules.subjects.service import get_subjects_service, SubjectsService
from modules.subjects.schema import (
    SubjectsListResponse,
    SubjectSchema,
)

router = APIRouter(
    prefix="/subjects",
    tags=["Subjects"],
)


@router.get("", response_model=ReturnType[SubjectsListResponse], status_code=200)
async def get_subjects(
    category: str | None = Query(None, description="Filter by category (sciences, arts, commercial, general)"),
    search: str | None = Query(None, description="Search subject name, display name, code, or alias"),
    exam_type: str | None = Query(None, alias="examType", description="Filter by exam type (waec, jamb, neco, post_utme)"),
    service: SubjectsService = Depends(get_subjects_service),
) -> ReturnType[SubjectsListResponse]:
    try:
        return await service.get_subjects(
            category=category, search=search, exam_type=exam_type
        )
    except Exception as e:
        logger.error("Failed to get subjects: " + str(e))
        raise BadRequestException(str(e))


@router.get("/{name}", response_model=ReturnType[SubjectSchema], status_code=200)
async def get_subject_by_name(
    name: str,
    service: SubjectsService = Depends(get_subjects_service),
) -> ReturnType[SubjectSchema]:
    try:
        return await service.get_subject_by_name(name)
    except Exception as e:
        logger.error(f"Failed to get subject '{name}': " + str(e))
        raise BadRequestException(str(e))
