from fastapi import Depends
from sqlalchemy import select, func, or_
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from common.classes.return_type import ReturnType, Pagination
from common.database import get_db
from common.logger import logger
from common.exceptions.bad_request_exception import BadRequestException
import json
import uuid
from sqlalchemy.orm.attributes import flag_modified
from models.examination_model import Examination
from models.answer_model import Answer
from models.question_model import Question
from modules.questions.service import get_subject_variants, get_examtype_variants, QuestionsService
from modules.questions.schema import QuestionItem
from modules.examination.schema import (
    CreateExamination,
    UpdateExamination,
    ExaminationReturn,
    CreateAnswer,
    AnswerReturn,
)


def get_all_subject_variants(subjects: list[str]) -> set[str]:
    variants = set()
    for s in subjects:
        if not s or not s.strip():
            continue
        cleaned = s.strip().lower()
        variants.add(cleaned)
        variants.add(cleaned.replace("-", " "))
        variants.add(cleaned.replace(" ", "-"))
        variants.add(cleaned.replace("-", ""))
        variants.add(cleaned.replace(" ", ""))
        for v in get_subject_variants(cleaned):
            v_clean = v.strip().lower()
            variants.add(v_clean)
            variants.add(v_clean.replace("-", " "))
            variants.add(v_clean.replace(" ", "-"))
            variants.add(v_clean.replace("-", ""))
            variants.add(v_clean.replace(" ", ""))
    return variants


def _parse_str_list(val) -> list[str]:
    if not val:
        return []
    if isinstance(val, str):
        try:
            parsed = json.loads(val)
            if isinstance(parsed, list):
                return [str(x) for x in parsed]
        except Exception:
            pass
        return [val]
    if isinstance(val, list):
        if val and isinstance(val[0], str) and val[0] == "[" and val[-1] == "]":
            try:
                parsed = json.loads("".join(val))
                if isinstance(parsed, list):
                    return [str(x) for x in parsed]
            except Exception:
                pass
        return [str(x) for x in val]
    return [str(x) for x in val]


class ExaminationService:
    def __init__(self, db: AsyncSession | None = None):
        self.db = db

    async def fetch_question_ids_for_examination(
        self,
        subjects: list[str],
        count_per_subject: int,
        exam_type: str | None = None,
        exam_year: str | None = None,
    ) -> list[int]:
        """
        Efficiently fetches question IDs for each subject based on count_per_subject.
        Selects only Question.id to minimize memory and network overhead.
        Only fetches questions for the specified subjects.
        Includes fallback stages if specific year or exam body has fewer questions.
        """
        if not self.db:
            raise BadRequestException("Database session not initialized")

        clean_subjects: list[str] = []
        for s in subjects:
            if s and s.strip():
                s_clean = s.strip()
                if s_clean not in clean_subjects:
                    clean_subjects.append(s_clean)

        if not clean_subjects or count_per_subject <= 0:
            return []

        type_variants = get_examtype_variants(exam_type) if exam_type else []

        is_valid_year = bool(
            exam_year
            and str(exam_year).strip().lower() not in ["all", "any", "random", "mixed", "none", ""]
        )
        clean_year = str(exam_year).strip() if is_valid_year else None

        all_ids: list[int] = []

        for subject in clean_subjects:
            subj_variants = get_subject_variants(subject)
            subj_condition = or_(
                func.lower(Question.subject).in_(subj_variants),
                (
                    or_(Question.subject.is_(None), Question.subject == "")
                    & func.lower(Question.category).in_(subj_variants)
                ),
            )

            # Base filters for subject
            base_filters = [
                Question.isDeleted == False,
                subj_condition,
            ]
            if type_variants:
                base_filters.append(func.lower(Question.examtype).in_(type_variants))

            # Exclude already picked questions across all subjects to prevent duplicates
            if all_ids:
                base_filters.append(Question.id.not_in(all_ids))

            # Primary attempt: Filter by subject, type and specific year (if given)
            filters_q1 = list(base_filters)
            if clean_year:
                filters_q1.append(func.trim(Question.examyear) == clean_year)

            stmt1 = (
                select(Question.id)
                .where(*filters_q1)
                .order_by(func.random())
                .limit(count_per_subject)
            )
            result1 = await self.db.execute(stmt1)
            subj_ids: list[int] = list(result1.scalars().all())

            # Fallback 1: If clean_year did not yield enough questions, supplement across any year
            if clean_year and len(subj_ids) < count_per_subject:
                remaining = count_per_subject - len(subj_ids)
                filters_q2 = list(base_filters)
                exclude_ids = list(all_ids) + list(subj_ids)
                if exclude_ids:
                    filters_q2.append(Question.id.not_in(exclude_ids))
                stmt2 = (
                    select(Question.id)
                    .where(*filters_q2)
                    .order_by(func.random())
                    .limit(remaining)
                )
                result2 = await self.db.execute(stmt2)
                subj_ids.extend(result2.scalars().all())

            # Fallback 2: If exam_type did not yield enough questions, supplement across any exam type
            if type_variants and len(subj_ids) < count_per_subject:
                remaining = count_per_subject - len(subj_ids)
                filters_q3 = [
                    Question.isDeleted == False,
                    subj_condition,
                ]
                exclude_ids = list(all_ids) + list(subj_ids)
                if exclude_ids:
                    filters_q3.append(Question.id.not_in(exclude_ids))
                stmt3 = (
                    select(Question.id)
                    .where(*filters_q3)
                    .order_by(func.random())
                    .limit(remaining)
                )
                result3 = await self.db.execute(stmt3)
                subj_ids.extend(result3.scalars().all())

            logger.info(
                f"Selected {len(subj_ids)} questions for subject '{subject}' "
                f"(requested: {count_per_subject}, exam_type: {exam_type}, exam_year: {exam_year})"
            )
            all_ids.extend(subj_ids)

        if not all_ids:
            logger.warning(f"No questions found in database for subjects: {clean_subjects}")
            raise BadRequestException(f"No questions found for the selected subject(s): {', '.join(clean_subjects)}")

        return all_ids

    async def create_examination(
        self, body: CreateExamination
    ) -> ReturnType[ExaminationReturn]:
        if not self.db:
            raise BadRequestException("Database session not initialized")

        clean_subjects: list[str] = []
        for s in (body.subjects or []):
            if s and s.strip():
                s_clean = s.strip()
                if s_clean not in clean_subjects:
                    clean_subjects.append(s_clean)

        if not clean_subjects:
            raise BadRequestException("At least one subject must be specified")

        exam_type_str = (
            body.exam_type.value
            if hasattr(body.exam_type, "value")
            else str(body.exam_type)
        )
        type_str = body.type.value if hasattr(body.type, "value") else str(body.type)

        # Determine questions IDs: only subjects listed in subject array are fetched
        if (body.total_question and body.total_question > 0) or not body.questions_ids:
            count_per_subject = body.total_question if (body.total_question and body.total_question > 0) else 10
            raw_questions_ids = await self.fetch_question_ids_for_examination(
                subjects=clean_subjects,
                count_per_subject=count_per_subject,
                exam_type=exam_type_str,
                exam_year=body.exam_year,
            )
        elif body.questions_ids:
            raw_questions_ids = list(body.questions_ids)
        else:
            raw_questions_ids = []

        # Before sending back the response, remove any question that does not match the selected subjects
        allowed_variants = get_all_subject_variants(clean_subjects)

        filtered_questions_ids: list[int] = []
        filtered_question_items: list[QuestionItem] = []

        if raw_questions_ids:
            unique_qids = list(dict.fromkeys(raw_questions_ids))
            q_stmt = select(Question).where(
                Question.id.in_(unique_qids),
                Question.isDeleted == False,
            )
            q_res = await self.db.execute(q_stmt)
            fetched_questions = list(q_res.scalars().all())

            # Fallback for external_id if any IDs were not resolved by primary key id
            found_ids = {q.id for q in fetched_questions}
            missing_ids = [qid for qid in unique_qids if qid not in found_ids]
            if missing_ids:
                stmt_ext = select(Question).where(
                    Question.external_id.in_(missing_ids),
                    Question.isDeleted == False,
                )
                result_ext = await self.db.execute(stmt_ext)
                fetched_questions.extend(result_ext.scalars().all())

            valid_questions_by_id: dict[int, Question] = {}
            for q in fetched_questions:
                q_subj = (q.subject or "").strip().lower()
                q_cat = (q.category or "").strip().lower()

                matches = False
                if q_subj:
                    if q_subj in allowed_variants or any(v in allowed_variants for v in get_subject_variants(q_subj)):
                        matches = True
                elif q_cat:
                    if q_cat in allowed_variants or any(v in allowed_variants for v in get_subject_variants(q_cat)):
                        matches = True

                if matches:
                    valid_questions_by_id[q.id] = q
                    if q.external_id is not None:
                        valid_questions_by_id[q.external_id] = q

            seen_ids = set()
            for qid in raw_questions_ids:
                q_obj = valid_questions_by_id.get(qid)
                if q_obj and q_obj.id not in seen_ids:
                    filtered_questions_ids.append(q_obj.id)
                    filtered_question_items.append(QuestionsService._to_question_item(q_obj))
                    seen_ids.add(q_obj.id)

        if not filtered_questions_ids:
            logger.warning(f"No questions found matching selected subjects: {clean_subjects}")
            raise BadRequestException(f"No questions found matching selected subject(s): {', '.join(clean_subjects)}")

        total_question_val = len(filtered_questions_ids)

        examination = Examination(
            user_id=body.user_id,
            type=type_str,
            subjects=clean_subjects,
            total_question=total_question_val,
            total_score=body.total_score,
            time=body.time,
            total_questions_answered=body.total_questions_answered or 0,
            total_questions_failed=body.total_questions_failed or 0,
            questions_ids=filtered_questions_ids,
            correct_questions=body.correct_questions,
            failed_questions=body.failed_questions,
            exam_year=body.exam_year,
            exam_type=exam_type_str,
        )
        self.db.add(examination)
        await self.db.commit()
        await self.db.refresh(examination)
        examination.questions = filtered_question_items

        logger.info(f"Examination created with id={examination.id}, total questions={len(filtered_questions_ids)}")

        ret_data = ExaminationReturn.model_validate(examination)
        ret_data.questions = filtered_question_items

        return ReturnType[ExaminationReturn](
            success=True,
            message="Examination created successfully",
            data=ret_data,
        )

    async def update_examination(
        self, id: uuid.UUID, body: UpdateExamination
    ) -> ReturnType[ExaminationReturn]:
        if not self.db:
            raise BadRequestException("Database session not initialized")

        stmt = (
            select(Examination)
            .options(selectinload(Examination.answers))
            .where(Examination.id == id, Examination.isDeleted == False)
        )
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
            .options(selectinload(Examination.answers))
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

        stmt = (
            select(Examination)
            .options(selectinload(Examination.answers))
            .where(Examination.id == id, Examination.isDeleted == False)
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

    async def delete_examination(
        self, id: uuid.UUID
    ) -> ReturnType[ExaminationReturn]:
        if not self.db:
            raise BadRequestException("Database session not initialized")

        stmt = (
            select(Examination)
            .options(selectinload(Examination.answers))
            .where(Examination.id == id, Examination.isDeleted == False)
        )
        result = await self.db.execute(stmt)
        examination = result.scalars().first()
        if not examination:
            logger.error(f"Examination not found with id={id}")
            raise BadRequestException(f"Examination with id {id} not found")

        now = func.now()
        examination.isDeleted = True
        examination.deleted_at = now
        for answer in examination.answers:
            if not answer.isDeleted:
                answer.isDeleted = True
                answer.deleted_at = now

        await self.db.commit()
        await self.db.refresh(examination)
        logger.info(f"Examination deleted with id={id}")
        return ReturnType[ExaminationReturn](
            success=True,
            message="Examination deleted successfully",
            data=ExaminationReturn.model_validate(examination),
        )

    async def create_answer(
        self, body: CreateAnswer
    ) -> ReturnType[AnswerReturn]:
        if not self.db:
            raise BadRequestException("Database session not initialized")

        stmt = (
            select(Examination)
            .options(selectinload(Examination.answers))
            .where(Examination.id == body.examination_id, Examination.isDeleted == False)
        )
        result = await self.db.execute(stmt)
        examination = result.scalars().first()
        if not examination:
            logger.error(f"Examination not found with id={body.examination_id}")
            raise BadRequestException(f"Examination with id {body.examination_id} not found")

        # Resolve user_id: use provided user_id or fallback to examination.user_id
        user_id = body.user_id or examination.user_id

        # Resolve correct_answer: use provided or look up from Question model
        correct_answer = body.correct_answer
        if not correct_answer:
            q_stmt = select(Question).where(
                or_(Question.id == body.question_id, Question.external_id == body.question_id),
                Question.isDeleted == False,
            )
            q_res = await self.db.execute(q_stmt)
            q_obj = q_res.scalars().first()
            if q_obj and q_obj.answer:
                correct_answer = q_obj.answer

        is_correct = (
            body.picked_answer is not None
            and correct_answer is not None
            and body.picked_answer.strip().lower() == correct_answer.strip().lower()
        )
        question_id_str = str(body.question_id)

        # Check if answer for this question already exists for this examination (upsert)
        existing_answer_stmt = select(Answer).where(
            Answer.examination_id == body.examination_id,
            Answer.question_id == body.question_id,
            Answer.isDeleted == False,
        )
        existing_res = await self.db.execute(existing_answer_stmt)
        existing_answer = existing_res.scalars().first()

        current_correct = _parse_str_list(examination.correct_questions)
        current_failed = _parse_str_list(examination.failed_questions)

        if existing_answer:
            prev_was_correct = (
                existing_answer.picked_answer is not None
                and existing_answer.correct_answer is not None
                and existing_answer.picked_answer.strip().lower() == existing_answer.correct_answer.strip().lower()
            )
            existing_answer.picked_answer = body.picked_answer
            existing_answer.correct_answer = correct_answer
            if user_id:
                existing_answer.user_id = user_id
            answer = existing_answer

            if is_correct:
                if not prev_was_correct:
                    examination.total_questions_failed = max(0, (examination.total_questions_failed or 0) - 1)
                current_failed = [x for x in current_failed if str(x) != question_id_str]
                if question_id_str not in current_correct:
                    current_correct.append(question_id_str)
            else:
                if prev_was_correct:
                    examination.total_questions_failed = (examination.total_questions_failed or 0) + 1
                current_correct = [x for x in current_correct if str(x) != question_id_str]
                if question_id_str not in current_failed:
                    current_failed.append(question_id_str)
        else:
            answer = Answer(
                examination_id=body.examination_id,
                user_id=user_id,
                question_id=body.question_id,
                picked_answer=body.picked_answer,
                correct_answer=correct_answer,
            )
            self.db.add(answer)

            examination.total_questions_answered = (examination.total_questions_answered or 0) + 1
            if is_correct:
                if question_id_str not in current_correct:
                    current_correct.append(question_id_str)
            else:
                examination.total_questions_failed = (examination.total_questions_failed or 0) + 1
                if question_id_str not in current_failed:
                    current_failed.append(question_id_str)

        examination.correct_questions = list(current_correct)
        examination.failed_questions = list(current_failed)
        flag_modified(examination, "correct_questions")
        flag_modified(examination, "failed_questions")

        await self.db.commit()
        await self.db.refresh(answer)
        await self.db.refresh(examination)

        logger.info(f"Answer recorded with id={answer.id} for examination_id={examination.id}")
        return ReturnType[AnswerReturn](
            success=True,
            message="Answer created and examination updated successfully",
            data=AnswerReturn.model_validate(answer),
        )

    async def get_examination_answers(
        self, examination_id: uuid.UUID
    ) -> ReturnType[list[AnswerReturn]]:
        if not self.db:
            raise BadRequestException("Database session not initialized")

        stmt = (
            select(Answer)
            .where(Answer.examination_id == examination_id, Answer.isDeleted == False)
            .order_by(Answer.created_at.asc())
        )
        result = await self.db.execute(stmt)
        answers = list(result.scalars().all())
        data = [AnswerReturn.model_validate(a) for a in answers]

        return ReturnType[list[AnswerReturn]](
            success=True,
            message="Answers fetched successfully",
            data=data,
        )


def get_examination_service(
    db: AsyncSession = Depends(get_db),
) -> ExaminationService:
    return ExaminationService(db=db)

