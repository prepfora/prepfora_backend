import json
from typing import Any
from fastapi import Depends
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from common.classes.return_type import ReturnType, Pagination
from common.database import get_db
from common.logger import logger
from common.exceptions.bad_request_exception import BadRequestException
from models.question_model import Question
from modules.questions.schema import (
    QuestionSingleResponse,
    QuestionMultipleResponse,
    QuestionItem,
    QuestionsByIdsRequest,
    CreateCustomQuestion,
    UpdateCustomQuestion,
    CustomQuestionReturn,
)

SUBJECT_ALIASES: dict[str, list[str]] = {
    "english": ["english", "use-of-english", "english-language", "eng"],
    "mathematics": ["mathematics", "maths", "math", "general-mathematics", "mth"],
    "physics": ["physics", "phy"],
    "chemistry": ["chemistry", "chem", "chm"],
    "biology": ["biology", "bio"],
    "economics": ["economics", "econ", "eco"],
    "government": ["government", "govt", "gov"],
    "commerce": ["commerce", "com"],
    "accounting": ["accounting", "financial-accounting", "acc"],
    "crs": ["crk", "crs", "christian-religious-knowledge", "christian-religious-studies"],
    "irs": ["irk", "irs", "islamic-religious-knowledge", "islamic-religious-studies"],
    "geography": ["geography", "geo"],
    "civiceducation": ["civiledu", "civic-education", "civic", "civiceducation"],
    "insurance": ["insurance", "ins"],
    "currentaffairs": ["currentaffairs", "current-affairs", "general-paper"],
    "history": ["history", "his"],
    "literature": ["englishlit", "literature", "literature-in-english", "lit"],
    "agricultural-science": ["agricultural-science", "agric", "agric-science", "agr"],
}


def get_subject_variants(subject: str | None) -> list[str]:
    if not subject:
        return []
    s = subject.strip().lower()
    variants = {s, s.replace("-", " "), s.replace(" ", "-"), s.replace("-", ""), s.replace(" ", "")}
    for canonical, aliases in SUBJECT_ALIASES.items():
        all_alts = [canonical.lower()] + [a.lower() for a in aliases]
        if any(v in all_alts for v in variants):
            for a in all_alts:
                variants.add(a)
                variants.add(a.replace("-", " "))
                variants.add(a.replace(" ", "-"))
                variants.add(a.replace("-", ""))
                variants.add(a.replace(" ", ""))
            break
    return list(variants)


def get_examtype_variants(examtype: str | None) -> list[str]:
    if not examtype:
        return []
    t = str(examtype).strip().lower()
    if t in ["utme", "jamb"]:
        return ["utme", "jamb"]
    if t in ["post-utme", "post_utme", "postutme"]:
        return ["post-utme", "post_utme", "postutme"]
    return [t, t.replace("-", "_"), t.replace("_", "-")]


class QuestionsService:
    def __init__(self, db: AsyncSession | None = None):
        self.db = db

    @staticmethod
    def _to_question_item(q: Question) -> QuestionItem:
        option_data = q.option
        if isinstance(option_data, str):
            try:
                option_data = json.loads(option_data)
            except Exception:
                pass

        return QuestionItem(
            id=q.id,
            subject=q.subject or q.category or "",
            question=q.question,
            option=option_data if option_data is not None else {},
            section=q.section or "",
            image=q.image or "",
            answer=q.answer or "",
            solution=q.solution or "",
            examtype=q.examtype or "",
            examyear=q.examyear or "",
            hasPassage=q.has_passage,
            has_passage=q.has_passage,
            category=q.category or q.subject or "",
        )

    async def get_random_question(
        self,
        subject: str = "english",
        type: str | None = None,
        year: str | int | None = None,
    ) -> ReturnType[QuestionSingleResponse]:
        if not self.db:
            raise BadRequestException("Database session not initialized")
        try:
            logger.info(f"Fetching random question from DB for subject={subject}, type={type}, year={year}")
            filters = [Question.isDeleted == False]

            if subject and subject.strip().lower() not in ["all", "any"]:
                subj_variants = get_subject_variants(subject)
                filters.append(
                    or_(
                        func.lower(Question.subject).in_(subj_variants),
                        func.lower(Question.category).in_(subj_variants),
                    )
                )

            if type:
                type_variants = get_examtype_variants(type)
                filters.append(func.lower(Question.examtype).in_(type_variants))

            if year:
                filters.append(func.trim(Question.examyear) == str(year).strip())

            stmt = (
                select(Question)
                .where(*filters)
                .order_by(func.random())
                .limit(1)
            )
            result = await self.db.execute(stmt)
            question = result.scalars().first()

            if not question:
                msg = f"No questions found for subject '{subject}'"
                if type:
                    msg += f", type '{type}'"
                if year:
                    msg += f", year '{year}'"
                logger.warning(msg)
                raise BadRequestException(msg)

            item = self._to_question_item(question)
            single_resp = QuestionSingleResponse(
                subject=question.subject or subject,
                status=200,
                data=item,
            )
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
        page: int = 1,
        type: str | None = None,
        year: str | int | None = None,
        random: bool | None = None,
    ) -> ReturnType[QuestionMultipleResponse]:
        if not self.db:
            raise BadRequestException("Database session not initialized")
        try:
            logger.info(f"Fetching {limit} questions from DB for subject={subject}, page={page}, type={type}, year={year}, random={random}")
            if page < 1:
                raise BadRequestException("Page must be greater than 0")
            if limit < 1:
                raise BadRequestException("Limit must be greater than 0")

            filters = [Question.isDeleted == False]

            if subject and subject.strip().lower() not in ["all", "any"]:
                subj_variants = get_subject_variants(subject)
                filters.append(
                    or_(
                        func.lower(Question.subject).in_(subj_variants),
                        func.lower(Question.category).in_(subj_variants),
                    )
                )

            if type:
                type_variants = get_examtype_variants(type)
                filters.append(func.lower(Question.examtype).in_(type_variants))

            if year:
                filters.append(func.trim(Question.examyear) == str(year).strip())

            count_stmt = select(func.count()).select_from(Question).where(*filters)
            total_result = await self.db.execute(count_stmt)
            total = total_result.scalar_one()

            # Randomize by default for practice questions unless year or page > 1 is specified, or caller overrides random
            should_randomize = random if random is not None else (year is None and page == 1)

            stmt = select(Question).where(*filters)
            if should_randomize:
                stmt = stmt.order_by(func.random()).limit(limit)
            else:
                stmt = stmt.order_by(Question.id.asc()).offset((page - 1) * limit).limit(limit)

            result = await self.db.execute(stmt)
            questions = list(result.scalars().all())

            items = [self._to_question_item(q) for q in questions]
            total_pages = (total + limit - 1) // limit if total > 0 else 1

            multi_resp = QuestionMultipleResponse(
                subject=subject,
                status=200,
                data=items,
            )

            return ReturnType[QuestionMultipleResponse](
                success=True,
                message="Questions fetched successfully",
                data=multi_resp,
                pagination=Pagination(
                    total=total,
                    page=page,
                    per_page=limit,
                    total_pages=total_pages,
                ),
            )
        except BadRequestException:
            raise
        except Exception as e:
            logger.error(f"Error in get_multiple_questions: {str(e)}")
            raise BadRequestException(f"Failed to fetch questions: {str(e)}")

    async def get_question_by_id(
        self,
        id: int | str,
        subject: str | None = None,
    ) -> ReturnType[QuestionSingleResponse]:
        if not self.db:
            raise BadRequestException("Database session not initialized")
        try:
            logger.info(f"Fetching question by id={id} from DB")
            try:
                qid = int(id)
            except (ValueError, TypeError):
                raise BadRequestException(f"Invalid question ID: {id}")

            stmt = select(Question).where(
                or_(Question.id == qid, Question.external_id == qid),
                Question.isDeleted == False,
            )
            result = await self.db.execute(stmt)
            question = result.scalars().first()
            if not question:
                logger.error(f"Question not found with id={id}")
                raise BadRequestException(f"Question with id {id} not found")

            item = self._to_question_item(question)
            single_resp = QuestionSingleResponse(
                subject=question.subject or subject,
                status=200,
                data=item,
            )
            return ReturnType[QuestionSingleResponse](
                success=True,
                message="Question fetched successfully",
                data=single_resp,
            )
        except BadRequestException:
            raise
        except Exception as e:
            logger.error(f"Error in get_question_by_id: {str(e)}")
            raise BadRequestException(f"Failed to fetch question: {str(e)}")

    async def get_questions_by_ids(
        self,
        payload: QuestionsByIdsRequest | list[int] | list[str] | Any,
    ) -> ReturnType[list[QuestionItem]]:
        """
        High-performance question retrieval by an array of IDs.
        - Accepts QuestionsByIdsRequest, list of integers, list of strings, or comma-separated strings.
        - Runs an indexed primary key lookup on Question.id (O(1) index scan).
        - Automatically falls back to external_id if any IDs are not found on Question.id.
        - Preserves the exact ordering of the requested IDs.
        """
        if not self.db:
            raise BadRequestException("Database session not initialized")

        try:
            raw_list: list[Any] = []
            if isinstance(payload, QuestionsByIdsRequest):
                raw_list = payload.ids
            elif isinstance(payload, dict):
                raw_list = payload.get("ids") or payload.get("question_ids") or payload.get("questions_ids") or []
            elif isinstance(payload, list):
                raw_list = payload
            elif isinstance(payload, (int, str)):
                raw_list = [payload]

            clean_ids: list[int] = []
            for item in raw_list:
                if isinstance(item, int):
                    clean_ids.append(item)
                elif isinstance(item, str):
                    for part in item.split(","):
                        part = part.strip()
                        if part.isdigit() or (part.startswith("-") and part[1:].isdigit()):
                            clean_ids.append(int(part))

            if not clean_ids:
                return ReturnType[list[QuestionItem]](
                    success=True,
                    message="Questions fetched successfully",
                    data=[],
                )

            # Deduplicate for SQL query efficiency
            unique_ids = list(dict.fromkeys(clean_ids))

            # Primary key index lookup
            stmt = (
                select(Question)
                .where(
                    Question.id.in_(unique_ids),
                    Question.isDeleted == False,
                )
            )
            result = await self.db.execute(stmt)
            questions = list(result.scalars().all())

            # Fallback for external_id if any IDs were not resolved by primary key id
            found_ids = {q.id for q in questions}
            missing_ids = [qid for qid in unique_ids if qid not in found_ids]
            if missing_ids:
                stmt_ext = (
                    select(Question)
                    .where(
                        Question.external_id.in_(missing_ids),
                        Question.isDeleted == False,
                    )
                )
                result_ext = await self.db.execute(stmt_ext)
                questions.extend(result_ext.scalars().all())

            # Map by id and external_id
            items_by_id: dict[int, QuestionItem] = {}
            for q in questions:
                item = self._to_question_item(q)
                items_by_id[q.id] = item
                if q.external_id is not None and q.external_id not in items_by_id:
                    items_by_id[q.external_id] = item

            # Preserve exact order of requested clean_ids
            ordered_items: list[QuestionItem] = []
            seen = set()
            for qid in clean_ids:
                if qid in items_by_id and qid not in seen:
                    seen.add(qid)
                    ordered_items.append(items_by_id[qid])

            logger.info(f"Retrieved {len(ordered_items)} questions for {len(clean_ids)} requested IDs")
            return ReturnType[list[QuestionItem]](
                success=True,
                message="Questions fetched successfully",
                data=ordered_items,
            )
        except BadRequestException:
            raise
        except Exception as e:
            logger.error(f"Error in get_questions_by_ids: {str(e)}")
            raise BadRequestException(f"Failed to fetch questions by IDs: {str(e)}")

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
            subject=body.subject,
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
        subject: str | None = None,
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
        if subject and subject.strip().lower() not in ["all", "any"]:
            subj_variants = get_subject_variants(subject)
            filters.append(
                or_(
                    func.lower(Question.subject).in_(subj_variants),
                    func.lower(Question.category).in_(subj_variants),
                )
            )
        if category:
            filters.append(func.lower(Question.category) == category.strip().lower())
        if examtype:
            type_variants = get_examtype_variants(examtype)
            filters.append(func.lower(Question.examtype).in_(type_variants))

        count_stmt = select(func.count()).select_from(Question).where(*filters)
        total_result = await self.db.execute(count_stmt)
        total = total_result.scalar_one()

        stmt = (
            select(Question)
            .where(*filters)
            .order_by(Question.id.asc())
            .offset((page - 1) * limit)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        questions = list(result.scalars().all())
        data = [CustomQuestionReturn.model_validate(q) for q in questions]
        total_pages = (total + limit - 1) // limit if total > 0 else 1

        return ReturnType[list[CustomQuestionReturn]](
            success=True,
            message="Custom questions fetched successfully",
            data=data,
            pagination=Pagination(
                total=total,
                page=page,
                per_page=limit,
                total_pages=total_pages,
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

        if body.subject is not None:
            question.subject = body.subject
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