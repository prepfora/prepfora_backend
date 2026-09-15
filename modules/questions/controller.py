from fastapi import APIRouter, Depends, Query, Path
from common.classes.return_type import ReturnType
from common.exceptions.bad_request_exception import BadRequestException
from common.logger import logger
from modules.questions.service import get_questions_service, QuestionsService
import uuid
from models.examination_model import ExaminationType, Type
from modules.questions.schema import (
    ExamType,
    QuestionSingleResponse,
    QuestionMultipleResponse,
    CreateCustomQuestion,
    UpdateCustomQuestion,
    CustomQuestionReturn,
    CreateExamination,
    UpdateExamination,
    ExaminationReturn,
)


router = APIRouter(
    prefix="/questions",
    tags=["Questions"],
)


@router.get("/random", response_model=ReturnType[QuestionSingleResponse], status_code=200)
async def get_random_question(
    subject: str = Query("english", description="Subject name (e.g. english, mathematics, physics)"),
    type: ExamType | str | None = Query(None, description="Exam type (e.g. utme, waec, neco, post-utme)"),
    year: str | None = Query(None, description="Exam year (e.g. 2020)"),
    service: QuestionsService = Depends(get_questions_service),
) -> ReturnType[QuestionSingleResponse]:
    try:
        return await service.get_random_question(subject=subject, type=type, year=year)
    except Exception as e:
        logger.error("Failed to get random question: " + str(e))
        raise BadRequestException(str(e))


@router.get("", response_model=ReturnType[QuestionMultipleResponse], status_code=200)
async def get_questions(
    subject: str = Query("english", description="Subject name (e.g. english, mathematics, physics)"),
    limit: int = Query(10, ge=1, le=50, description="Number of questions to return (max 50)"),
    type: ExamType | str | None = Query(None, description="Exam type (e.g. utme, waec, neco, post-utme)"),
    year: str | None = Query(None, description="Exam year (e.g. 2020)"),
    service: QuestionsService = Depends(get_questions_service),
) -> ReturnType[QuestionMultipleResponse]:
    try:
        return await service.get_multiple_questions(
            subject=subject, limit=limit, type=type, year=year
        )
    except Exception as e:
        logger.error("Failed to get questions: " + str(e))
        raise BadRequestException(str(e))


@router.get("/{id}", response_model=ReturnType[QuestionSingleResponse], status_code=200)
async def get_question_by_id(
    id: int | str = Path(..., description="Question ID"),
    subject: str = Query("english", description="Subject name (e.g. english, mathematics, physics)"),
    service: QuestionsService = Depends(get_questions_service),
) -> ReturnType[QuestionSingleResponse]:
    try:
        return await service.get_question_by_id(id=id, subject=subject)
    except Exception as e:
        logger.error("Failed to get question by ID: " + str(e))
        raise BadRequestException(str(e))


# CUSTOM QUESTION ENDPOINTS

@router.post("/custom", response_model=ReturnType[CustomQuestionReturn], status_code=201)
async def create_custom_question(
    question: CreateCustomQuestion,
    service: QuestionsService = Depends(get_questions_service),
) -> ReturnType[CustomQuestionReturn]:
    try:
        return await service.create_custom_question(question)
    except Exception as e:
        logger.error("Failed to create custom question: " + str(e))
        raise BadRequestException(str(e))


@router.get("/custom", response_model=ReturnType[list[CustomQuestionReturn]], status_code=200)
async def get_custom_questions(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    category: str | None = Query(None, description="Filter by category"),
    examtype: ExamType | str | None = Query(None, description="Filter by exam type (waec, utme, neco, post-utme)"),
    service: QuestionsService = Depends(get_questions_service),
) -> ReturnType[list[CustomQuestionReturn]]:
    try:
        return await service.get_custom_questions(
            page=page, limit=limit, category=category, examtype=examtype
        )
    except Exception as e:
        logger.error("Failed to get custom questions: " + str(e))
        raise BadRequestException(str(e))


@router.get("/custom/{id}", response_model=ReturnType[CustomQuestionReturn], status_code=200)
async def get_custom_question_by_id(
    id: int = Path(..., description="Custom question ID"),
    service: QuestionsService = Depends(get_questions_service),
) -> ReturnType[CustomQuestionReturn]:
    try:
        return await service.get_custom_question_by_id(id)
    except Exception as e:
        logger.error("Failed to get custom question by ID: " + str(e))
        raise BadRequestException(str(e))


@router.put("/custom/{id}", response_model=ReturnType[CustomQuestionReturn], status_code=200)
async def update_custom_question(
    question: UpdateCustomQuestion,
    id: int = Path(..., description="Custom question ID"),
    service: QuestionsService = Depends(get_questions_service),
) -> ReturnType[CustomQuestionReturn]:
    try:
        return await service.update_custom_question(id, question)
    except Exception as e:
        logger.error("Failed to update custom question: " + str(e))
        raise BadRequestException(str(e))


@router.delete("/custom/{id}", response_model=ReturnType[CustomQuestionReturn], status_code=200)
async def delete_custom_question(
    id: int = Path(..., description="Custom question ID"),
    service: QuestionsService = Depends(get_questions_service),
) -> ReturnType[CustomQuestionReturn]:
    try:
        return await service.delete_custom_question(id)
    except Exception as e:
        logger.error("Failed to delete custom question: " + str(e))
        raise BadRequestException(str(e))


# EXAMINATION ENDPOINTS

@router.get("/examination", response_model=ReturnType[list[ExaminationReturn]], status_code=200)
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
    service: QuestionsService = Depends(get_questions_service),
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


@router.get("/examination/{id}", response_model=ReturnType[ExaminationReturn], status_code=200)
async def get_examination_by_id(
    id: uuid.UUID = Path(..., description="Examination ID"),
    service: QuestionsService = Depends(get_questions_service),
) -> ReturnType[ExaminationReturn]:
    try:
        return await service.get_examination_by_id(id)
    except Exception as e:
        logger.error("Failed to get examination by ID: " + str(e))
        raise BadRequestException(str(e))


@router.post("/examination", response_model=ReturnType[ExaminationReturn], status_code=201)
async def create_examination(
    examination: CreateExamination,
    service: QuestionsService = Depends(get_questions_service),
) -> ReturnType[ExaminationReturn]:
    try:
        return await service.create_examination(examination)
    except Exception as e:
        logger.error("Failed to create examination: " + str(e))
        raise BadRequestException(str(e))


@router.put("/examination/{id}", response_model=ReturnType[ExaminationReturn], status_code=200)
async def update_examination(
    examination: UpdateExamination,
    id: uuid.UUID = Path(..., description="Examination ID"),
    service: QuestionsService = Depends(get_questions_service),
) -> ReturnType[ExaminationReturn]:
    try:
        return await service.update_examination(id, examination)
    except Exception as e:
        logger.error("Failed to update examination: " + str(e))
        raise BadRequestException(str(e))


