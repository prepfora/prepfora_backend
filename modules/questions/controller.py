from fastapi import APIRouter, Depends, Query, Path, Body
from common.classes.return_type import ReturnType
from common.exceptions.bad_request_exception import BadRequestException
from common.logger import logger
from modules.questions.service import get_questions_service, QuestionsService
from modules.questions.schema import (
    ExamType,
    QuestionSingleResponse,
    QuestionMultipleResponse,
    QuestionItem,
    QuestionsByIdsRequest,
    CreateCustomQuestion,
    UpdateCustomQuestion,
    CustomQuestionReturn,
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


# CUSTOM QUESTION ENDPOINTS (Registered before /{id} to prevent path collision)

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
    subject: str | None = Query(None, description="Filter by subject"),
    category: str | None = Query(None, description="Filter by category"),
    examtype: ExamType | str | None = Query(None, description="Filter by exam type (waec, utme, neco, post-utme)"),
    service: QuestionsService = Depends(get_questions_service),
) -> ReturnType[list[CustomQuestionReturn]]:
    try:
        return await service.get_custom_questions(
            page=page, limit=limit, subject=subject, category=category, examtype=examtype
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


@router.post("/batch", response_model=ReturnType[list[QuestionItem]], status_code=200)
async def get_questions_by_ids(
    payload: QuestionsByIdsRequest | list[int] = Body(
        ...,
        description="Array of question IDs (can be [1,2,3] or {'ids': [1,2,3]} or {'question_ids': [1,2,3]})",
    ),
    service: QuestionsService = Depends(get_questions_service),
) -> ReturnType[list[QuestionItem]]:
    try:
        return await service.get_questions_by_ids(payload)
    except Exception as e:
        logger.error("Failed to get questions by IDs: " + str(e))
        raise BadRequestException(str(e))


@router.get("/batch", response_model=ReturnType[list[QuestionItem]], status_code=200)
async def get_questions_by_ids_get(
    ids: list[str] = Query(default=[], description="List of question IDs (comma-separated or repeated)"),
    service: QuestionsService = Depends(get_questions_service),
) -> ReturnType[list[QuestionItem]]:
    try:
        return await service.get_questions_by_ids(ids)
    except Exception as e:
        logger.error("Failed to get questions by IDs: " + str(e))
        raise BadRequestException(str(e))


@router.get("", response_model=ReturnType[QuestionMultipleResponse], status_code=200)
async def get_questions(
    subject: str = Query("english", description="Subject name (e.g. english, mathematics, physics)"),
    limit: int = Query(10, ge=1, le=100, description="Number of questions to return (max 100)"),
    page: int = Query(1, ge=1, description="Page number"),
    type: ExamType | str | None = Query(None, description="Exam type (e.g. utme, waec, neco, post-utme)"),
    year: str | None = Query(None, description="Exam year (e.g. 2020)"),
    random: bool | None = Query(None, description="Whether to randomize question order"),
    service: QuestionsService = Depends(get_questions_service),
) -> ReturnType[QuestionMultipleResponse]:
    try:
        return await service.get_multiple_questions(
            subject=subject, limit=limit, page=page, type=type, year=year, random=random
        )
    except Exception as e:
        logger.error("Failed to get questions: " + str(e))
        raise BadRequestException(str(e))


@router.get("/{id}", response_model=ReturnType[QuestionSingleResponse], status_code=200)
async def get_question_by_id(
    id: int = Path(..., description="Question ID"),
    subject: str | None = Query(None, description="Subject name (optional, e.g. english, mathematics, physics)"),
    service: QuestionsService = Depends(get_questions_service),
) -> ReturnType[QuestionSingleResponse]:
    try:
        return await service.get_question_by_id(id=id, subject=subject)
    except Exception as e:
        logger.error("Failed to get question by ID: " + str(e))
        raise BadRequestException(str(e))
