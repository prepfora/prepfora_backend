from fastapi import Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from common.classes.return_type import ReturnType, Pagination
from common.database import get_db
from common.logger import logger
from common.exceptions.bad_request_exception import BadRequestException
import uuid
from models.examination_model import Examination
from modules.examination.schema import (
    CreateExamination,
    UpdateExamination,
    ExaminationReturn,
)


class ExaminationService:
    def __init__(self, db: AsyncSession | None = None):
        self.db = db

    async def create_examination(
        self, body: CreateExamination
    ) -> ReturnType[ExaminationReturn]:
        if not self.db:
            raise BadRequestException("Database session not initialized")

        exam_type_str = (
            body.exam_type.value
            if hasattr(body.exam_type, "value")
            else str(body.exam_type)
        )
        type_str = body.type.value if hasattr(body.type, "value") else str(body.type)

        examination = Examination(
            user_id=body.user_id,
            type=type_str,
            subjects=body.subjects,
            total_question=body.total_question,
            total_score=body.total_score,
            time=body.time,
            total_questions_answered=body.total_questions_answered or 0,
            total_questions_failed=body.total_questions_failed or 0,
            questions_ids=body.questions_ids,
            correct_questions=body.correct_questions,
            failed_questions=body.failed_questions,
            exam_year=body.exam_year,
            exam_type=exam_type_str,
        )
        self.db.add(examination)
        await self.db.commit()
        await self.db.refresh(examination)
        logger.info(f"Examination created with id={examination.id}")
        return ReturnType[ExaminationReturn](
            success=True,
            message="Examination created successfully",
            data=ExaminationReturn.model_validate(examination),
        )

    async def update_examination(
        self, id: uuid.UUID, body: UpdateExamination
    ) -> ReturnType[ExaminationReturn]:
        if not self.db:
            raise BadRequestException("Database session not initialized")

        stmt = select(Examination).where(Examination.id == id)
        result = await self.db.execute(stmt)
        examination = result.scalars().first()
        if not examination:
            logger.error(f"Examination not found with id={id}")
            raise BadRequestException(f"Examination with id {id} not found")

        if body.type is not None:
            examination.type = (
                body.type.value if hasattr(body.type, "value") else str(body.type)
            )
        if body.subjects is not None:
            examination.subjects = body.subjects
        if body.total_question is not None:
            examination.total_question = body.total_question
        if body.total_score is not None:
            examination.total_score = body.total_score
        if body.time is not None:
            examination.time = body.time
        if body.total_questions_answered is not None:
            examination.total_questions_answered = body.total_questions_answered
        if body.total_questions_failed is not None:
            examination.total_questions_failed = body.total_questions_failed
        if body.questions_ids is not None:
            examination.questions_ids = body.questions_ids
        if body.correct_questions is not None:
            examination.correct_questions = body.correct_questions
        if body.failed_questions is not None:
            examination.failed_questions = body.failed_questions
        if body.exam_year is not None:
            examination.exam_year = body.exam_year
        if body.exam_type is not None:
            examination.exam_type = (
                body.exam_type.value
                if hasattr(body.exam_type, "value")
                else str(body.exam_type)
            )

        await self.db.commit()
        await self.db.refresh(examination)
        logger.info(f"Examination updated with id={id}")
        return ReturnType[ExaminationReturn](
            success=True,
            message="Examination updated successfully",
            data=ExaminationReturn.model_validate(examination),
        )

    async def get_user_examinations(
        self,
        page: int = 1,
        limit: int = 20,
        user_id: uuid.UUID | str | None = None,
        subject: str | None = None,
        subject_type: str | None = None,
        exam_type: str | None = None,
        year: str | int | None = None,
        exam_year: str | int | None = None,
        type: str | None = None,
    ) -> ReturnType[list[ExaminationReturn]]:
        if not self.db:
            raise BadRequestException("Database session not initialized")
        if page < 1:
            raise BadRequestException("Page must be greater than 0")
        if limit < 1:
            raise BadRequestException("Limit must be greater than 0")

        filters = [Examination.isDeleted == False]

        if user_id:
            if isinstance(user_id, str):
                try:
                    user_id = uuid.UUID(user_id)
                except ValueError:
                    raise BadRequestException("Invalid user_id format")
            filters.append(Examination.user_id == user_id)

        target_subject = subject or subject_type
        if target_subject:
            filters.append(Examination.subjects.any(target_subject))

        target_exam_type = (
            exam_type.value
            if hasattr(exam_type, "value")
            else (str(exam_type) if exam_type else None)
        )
        if target_exam_type:
            filters.append(Examination.exam_type == target_exam_type)

        target_year = year if year is not None else exam_year
        if target_year is not None:
            filters.append(Examination.exam_year == str(target_year))

        target_type = (
            type.value
            if hasattr(type, "value")
            else (str(type) if type else None)
        )
        if target_type:
            filters.append(Examination.type == target_type)

        count_stmt = select(func.count()).select_from(Examination).where(*filters)
        total_result = await self.db.execute(count_stmt)
        total = total_result.scalar_one()

        stmt = (
            select(Examination)
            .where(*filters)
            .order_by(Examination.created_at.desc())
            .offset((page - 1) * limit)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        examinations = list(result.scalars().all())
        data = [ExaminationReturn.model_validate(exam) for exam in examinations]

        return ReturnType[list[ExaminationReturn]](
            success=True,
            message="User examinations fetched successfully",
            data=data,
            pagination=Pagination(
                total=total,
                page=page,
                per_page=limit,
            ),
        )

    async def get_examination_by_id(
        self, id: uuid.UUID
    ) -> ReturnType[ExaminationReturn]:
        if not self.db:
            raise BadRequestException("Database session not initialized")

        stmt = select(Examination).where(
            Examination.id == id, Examination.isDeleted == False
        )
        result = await self.db.execute(stmt)
        examination = result.scalars().first()
        if not examination:
            logger.error(f"Examination not found with id={id}")
            raise BadRequestException(f"Examination with id {id} not found")

        return ReturnType[ExaminationReturn](
            success=True,
            message="Examination fetched successfully",
            data=ExaminationReturn.model_validate(examination),
        )


def get_examination_service(
    db: AsyncSession = Depends(get_db),
) -> ExaminationService:
    return ExaminationService(db=db)
