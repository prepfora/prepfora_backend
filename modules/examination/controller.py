from fastapi import APIRouter, Depends, Query, Path
from common.classes.return_type import ReturnType
from common.exceptions.bad_request_exception import BadRequestException
from common.logger import logger
from modules.examination.service import get_examination_service, ExaminationService
import uuid
from models.examination_model import ExaminationType, Type
from modules.examination.schema import (
    CreateExamination,
    UpdateExamination,
    ExaminationReturn,
    CreateAnswer,
    AnswerReturn,
)

router = APIRouter(
    prefix="/examination",
    tags=["Examination"],
)


@router.get("", response_model=ReturnType[list[ExaminationReturn]], status_code=200)
async def get_user_examinations(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    user_id: uuid.UUID | None = Query(None, description="Filter by user ID"),
    subject: str | None = Query(None, description="Filter by subject (e.g. english, mathematics)"),
    subject_type: str | None = Query(None, description="Filter by subject type"),
    exam_type: ExaminationType | str | None = Query(None, description="Filter by exam type (waec, utme, neco, post-utme)"),
    year: str | None = Query(None, description="Filter by exam year (e.g. 2020)"),
    exam_year: str | None = Query(None, description="Filter by exam year"),
    type: Type | str | None = Query(None, description="Filter by examination type (practice, mock)"),
    service: ExaminationService = Depends(get_examination_service),
) -> ReturnType[list[ExaminationReturn]]:
    try:
        return await service.get_user_examinations(
            page=page,
            limit=limit,
            user_id=user_id,
            subject=subject,
            subject_type=subject_type,
            exam_type=exam_type,
            year=year,
            exam_year=exam_year,
            type=type,
        )
    except Exception as e:
        logger.error("Failed to get user examinations: " + str(e))
        raise BadRequestException(str(e))


@router.post("/answer", response_model=ReturnType[AnswerReturn], status_code=201)
async def create_answer(
    answer: CreateAnswer,
    service: ExaminationService = Depends(get_examination_service),
) -> ReturnType[AnswerReturn]:
    try:
        return await service.create_answer(answer)
    except Exception as e:
        logger.error("Failed to create answer: " + str(e))
        raise BadRequestException(str(e))


@router.get("/{id}/answers", response_model=ReturnType[list[AnswerReturn]], status_code=200)
async def get_examination_answers(
    id: uuid.UUID = Path(..., description="Examination ID"),
    service: ExaminationService = Depends(get_examination_service),
) -> ReturnType[list[AnswerReturn]]:
    try:
        return await service.get_examination_answers(id)
    except Exception as e:
        logger.error("Failed to get examination answers: " + str(e))
        raise BadRequestException(str(e))


@router.get("/{id}", response_model=ReturnType[ExaminationReturn], status_code=200)
async def get_examination_by_id(
    id: uuid.UUID = Path(..., description="Examination ID"),
    service: ExaminationService = Depends(get_examination_service),
) -> ReturnType[ExaminationReturn]:
    try:
        return await service.get_examination_by_id(id)
    except Exception as e:
        logger.error("Failed to get examination by ID: " + str(e))
        raise BadRequestException(str(e))


@router.post("", response_model=ReturnType[ExaminationReturn], status_code=201)
async def create_examination(
    examination: CreateExamination,
    service: ExaminationService = Depends(get_examination_service),
) -> ReturnType[ExaminationReturn]:
    try:
        return await service.create_examination(examination)
    except Exception as e:
        logger.error("Failed to create examination: " + str(e))
        raise BadRequestException(str(e))


@router.put("/{id}", response_model=ReturnType[ExaminationReturn], status_code=200)
async def update_examination(
    examination: UpdateExamination,
    id: uuid.UUID = Path(..., description="Examination ID"),
    service: ExaminationService = Depends(get_examination_service),
) -> ReturnType[ExaminationReturn]:
    try:
        return await service.update_examination(id, examination)
    except Exception as e:
        logger.error("Failed to update examination: " + str(e))
        raise BadRequestException(str(e))

