from fastapi import APIRouter, Depends, Query
from common.classes.return_type import ReturnType
from common.exceptions.bad_request_exception import BadRequestException
from common.logger import logger
from modules.questions.service import get_questions_service, QuestionsService
from modules.questions.schema import (
    QuestionSingleResponse,
    QuestionMultipleResponse,
)

router = APIRouter(
    prefix="/questions",
    tags=["Questions"],
)


@router.get("/random", response_model=ReturnType[QuestionSingleResponse], status_code=200)
async def get_random_question(
    subject: str = Query("english", description="Subject name (e.g. english, mathematics, physics)"),
    type: str | None = Query(None, description="Exam type (e.g. utme, waec, neco, post-utme)"),
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
    type: str | None = Query(None, description="Exam type (e.g. utme, waec, neco, post-utme)"),
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
