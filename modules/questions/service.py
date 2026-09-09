import httpx
from fastapi import Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from common.config import settings
from common.classes.return_type import ReturnType, Pagination
from common.database import get_db
from common.logger import logger
from common.exceptions.bad_request_exception import BadRequestException
from models.question_model import Question
from modules.questions.schema import (
    QuestionSingleResponse,
    QuestionMultipleResponse,
    QuestionItem,
    CreateCustomQuestion,
    UpdateCustomQuestion,
    CustomQuestionReturn,
)

ALOC_BASE_URL = "https://questions.aloc.com.ng/api/v2"


class QuestionsService:
    def __init__(self, db: AsyncSession | None = None):
        self.db = db
        self.access_token = settings.aloc_access_token
        self.headers = {
            "AccessToken": self.access_token,
            "Accept": "application/json",
        }

    async def get_random_question(
        self,
        subject: str = "english",
        type: str | None = None,
        year: str | int | None = None,
    ) -> ReturnType[QuestionSingleResponse]:
        try:
            logger.info(f"Fetching random question for subject={subject}")
            params = {"subject": subject}
            if type:
                params["type"] = type
            if year:
                params["year"] = str(year)

            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.get(
                    f"{ALOC_BASE_URL}/q",
                    headers=self.headers,
                    params=params,
                )
                if response.status_code != 200:
                    logger.error(f"ALOC API Error: {response.text}")
                    raise BadRequestException("Failed to fetch question from ALOC API")

                res_data = response.json()
                single_resp = QuestionSingleResponse(**res_data)
                return ReturnType[QuestionSingleResponse](
                    success=True,
                    message="Question fetched successfully",
                    data=single_resp,
                )
        except BadRequestException:
            raise
        except Exception as e:
            logger.error(f"Error in get_random_question: {str(e)}")
            raise BadRequestException(f"Failed to fetch question: {str(e)}")

    async def get_multiple_questions(
        self,
        subject: str = "english",
        limit: int = 10,
        type: str | None = None,
        year: str | int | None = None,
    ) -> ReturnType[QuestionMultipleResponse]:
        try:
            logger.info(f"Fetching {limit} questions for subject={subject}")
            params = {"subject": subject}
            if type:
                params["type"] = type
            if year:
                params["year"] = str(year)

            endpoint = (
                f"{ALOC_BASE_URL}/q/{limit}"
                if limit and limit > 1
                else f"{ALOC_BASE_URL}/m"
            )

            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.get(
                    endpoint,
                    headers=self.headers,
                    params=params,
                )
                if response.status_code != 200:
                    logger.error(f"ALOC API Error: {response.text}")
                    raise BadRequestException(
                        "Failed to fetch questions from ALOC API"
                    )

                res_data = response.json()
                data_field = res_data.get("data", [])
                items = []

                if isinstance(data_field, list):
                    items = [QuestionItem(**item) for item in data_field]
                elif isinstance(data_field, dict):
                    items = [QuestionItem(**data_field)]

                multi_resp = QuestionMultipleResponse(
                    subject=res_data.get("subject", subject),
                    status=res_data.get("status", 200),
                    data=items,
                )

                return ReturnType[QuestionMultipleResponse](
                    success=True,
                    message="Questions fetched successfully",
                    data=multi_resp,
                )
        except BadRequestException:
            raise
        except Exception as e:
            logger.error(f"Error in get_multiple_questions: {str(e)}")
            raise BadRequestException(f"Failed to fetch questions: {str(e)}")

    # CUSTOM QUESTION CRUD OPERATIONS

    async def create_custom_question(
        self, body: CreateCustomQuestion
    ) -> ReturnType[CustomQuestionReturn]:
        if not self.db:
            raise BadRequestException("Database session not initialized")

        option_data = (
            body.option.model_dump()
            if hasattr(body.option, "model_dump")
            else body.option
        )

        question = Question(
            question=body.question,
            option=option_data,
            section=body.section,
            image=body.image,
            answer=body.answer,
            solution=body.solution,
            examtype=body.examtype,
            examyear=body.examyear,
            has_passage=body.has_passage,
            category=body.category,
        )
        self.db.add(question)
        await self.db.commit()
        await self.db.refresh(question)
        logger.info(f"Custom question created with id={question.id}")
        return ReturnType[CustomQuestionReturn](
            success=True,
            message="Question created successfully",
            data=CustomQuestionReturn.model_validate(question),
        )

    async def get_custom_questions(
        self,
        page: int = 1,
        limit: int = 20,
        category: str | None = None,
        examtype: str | None = None,
    ) -> ReturnType[list[CustomQuestionReturn]]:
        if not self.db:
            raise BadRequestException("Database session not initialized")
        if page < 1:
            raise BadRequestException("Page must be greater than 0")
        if limit < 1:
            raise BadRequestException("Limit must be greater than 0")

        filters = [Question.isDeleted == False]
        if category:
            filters.append(Question.category == category)
        if examtype:
            filters.append(Question.examtype == examtype)

        count_stmt = select(func.count()).select_from(Question).where(*filters)
        total_result = await self.db.execute(count_stmt)
        total = total_result.scalar_one()

        stmt = (
            select(Question)
            .where(*filters)
            .offset((page - 1) * limit)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        questions = list(result.scalars().all())
        data = [CustomQuestionReturn.model_validate(q) for q in questions]

        return ReturnType[list[CustomQuestionReturn]](
            success=True,
            message="Custom questions fetched successfully",
            data=data,
            pagination=Pagination(
                total=total,
                page=page,
                per_page=limit,
            ),
        )

    async def get_custom_question_by_id(
        self, id: int
    ) -> ReturnType[CustomQuestionReturn]:
        if not self.db:
            raise BadRequestException("Database session not initialized")

        stmt = select(Question).where(Question.id == id, Question.isDeleted == False)
        result = await self.db.execute(stmt)
        question = result.scalars().first()
        if not question:
            logger.error(f"Question not found with id={id}")
            raise BadRequestException(f"Question with id {id} not found")

        return ReturnType[CustomQuestionReturn](
            success=True,
            message="Question fetched successfully",
            data=CustomQuestionReturn.model_validate(question),
        )

    async def update_custom_question(
        self, id: int, body: UpdateCustomQuestion
    ) -> ReturnType[CustomQuestionReturn]:
        if not self.db:
            raise BadRequestException("Database session not initialized")

        stmt = select(Question).where(Question.id == id, Question.isDeleted == False)
        result = await self.db.execute(stmt)
        question = result.scalars().first()
        if not question:
            logger.error(f"Question not found with id={id}")
            raise BadRequestException(f"Question with id {id} not found")

        if body.question is not None:
            question.question = body.question
        if body.option is not None:
            question.option = (
                body.option.model_dump()
                if hasattr(body.option, "model_dump")
                else body.option
            )
        if body.section is not None:
            question.section = body.section
        if body.image is not None:
            question.image = body.image
        if body.answer is not None:
            question.answer = body.answer
        if body.solution is not None:
            question.solution = body.solution
        if body.examtype is not None:
            question.examtype = body.examtype
        if body.examyear is not None:
            question.examyear = body.examyear
        if body.has_passage is not None:
            question.has_passage = body.has_passage
        if body.category is not None:
            question.category = body.category

        await self.db.commit()
        await self.db.refresh(question)
        logger.info(f"Question updated with id={id}")
        return ReturnType[CustomQuestionReturn](
            success=True,
            message="Question updated successfully",
            data=CustomQuestionReturn.model_validate(question),
        )

    async def delete_custom_question(
        self, id: int
    ) -> ReturnType[CustomQuestionReturn]:
        if not self.db:
            raise BadRequestException("Database session not initialized")

        stmt = select(Question).where(Question.id == id, Question.isDeleted == False)
        result = await self.db.execute(stmt)
        question = result.scalars().first()
        if not question:
            logger.error(f"Question not found with id={id}")
            raise BadRequestException(f"Question with id {id} not found")

        question.isDeleted = True
        question.deleted_at = func.now()
        await self.db.commit()
        await self.db.refresh(question)
        logger.info(f"Question deleted with id={id}")
        return ReturnType[CustomQuestionReturn](
            success=True,
            message="Question deleted successfully",
            data=CustomQuestionReturn.model_validate(question),
        )


def get_questions_service(
    db: AsyncSession = Depends(get_db),
) -> QuestionsService:
    return QuestionsService(db=db)
