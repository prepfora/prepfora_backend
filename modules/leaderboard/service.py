import uuid
from fastapi import Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from common.classes.return_type import Pagination, ReturnType
from common.database import get_db
from common.exceptions.bad_request_exception import BadRequestException
from common.logger import logger
from models.examination_model import Examination
from models.user_model import User
from modules.leaderboard.schema import LeaderboardEntry, LeaderboardResponse
from modules.questions.service import get_examtype_variants


class LeaderboardService:
    def __init__(self, db: AsyncSession):
        self.db = db

    def _build_ranked_subquery(
        self,
        exam_type: str,
        exam_mode: str | None = None,
    ):
        type_variants = get_examtype_variants(exam_type)
        if not type_variants:
            raise BadRequestException("exam_type is required")

        effective_score = func.coalesce(Examination.score, Examination.total_score, 0.0)
        activity_ts = func.coalesce(
            Examination.completed_at, Examination.updated_at, Examination.created_at
        )

        filters = [
            Examination.isDeleted == False,
            User.isDeleted == False,
            func.lower(Examination.exam_type).in_(type_variants),
            (Examination.score.isnot(None)) | (Examination.total_score.isnot(None)),
        ]
        if exam_mode and exam_mode.strip():
            filters.append(func.lower(Examination.type) == exam_mode.strip().lower())

        agg_stmt = (
            select(
                User.id.label("user_id"),
                User.first_name.label("first_name"),
                User.last_name.label("last_name"),
                User.profile_picture.label("profile_picture"),
                User.university.label("university"),
                User.state.label("state"),
                User.prep_points.label("prep_points"),
                func.max(effective_score).label("best_score"),
                func.avg(effective_score).label("average_score"),
                func.count(Examination.id).label("total_exams"),
                func.max(activity_ts).label("last_exam_at"),
            )
            .join(User, User.id == Examination.user_id)
            .where(*filters)
            .group_by(
                User.id,
                User.first_name,
                User.last_name,
                User.profile_picture,
                User.university,
                User.state,
                User.prep_points,
            )
            .subquery("user_exam_stats")
        )

        ranked_stmt = select(
            func.row_number()
            .over(
                order_by=(
                    agg_stmt.c.best_score.desc(),
                    agg_stmt.c.average_score.desc(),
                    agg_stmt.c.total_exams.desc(),
                    agg_stmt.c.last_exam_at.asc(),
                )
            )
            .label("rank"),
            agg_stmt,
        ).subquery("ranked_leaderboard")

        return ranked_stmt

    @staticmethod
    def _row_to_entry(row, exam_type: str) -> LeaderboardEntry:
        return LeaderboardEntry(
            rank=int(row.rank),
            user_id=row.user_id,
            first_name=row.first_name,
            last_name=row.last_name,
            profile_picture=row.profile_picture,
            university=row.university,
            state=row.state,
            exam_type=exam_type.strip().lower(),
            best_score=round(float(row.best_score or 0.0), 2),
            average_score=round(float(row.average_score or 0.0), 2),
            total_exams=int(row.total_exams or 0),
            prep_points=int(row.prep_points or 0),
            last_exam_at=row.last_exam_at,
        )

    async def get_leaderboard(
        self,
        exam_type: str,
        exam_mode: str | None = None,
        page: int = 1,
        limit: int = 20,
        current_user_id: uuid.UUID | None = None,
    ) -> ReturnType[LeaderboardResponse]:
        if page < 1:
            raise BadRequestException("Page must be greater than 0")
        if limit < 1:
            raise BadRequestException("Limit must be greater than 0")

        ranked_sq = self._build_ranked_subquery(exam_type=exam_type, exam_mode=exam_mode)

        total_stmt = select(func.count()).select_from(ranked_sq)
        total = (await self.db.execute(total_stmt)).scalar() or 0

        page_stmt = (
            select(ranked_sq)
            .order_by(ranked_sq.c.rank.asc())
            .offset((page - 1) * limit)
            .limit(limit)
        )
        rows = (await self.db.execute(page_stmt)).all()
        entries = [self._row_to_entry(r, exam_type) for r in rows]

        current_user_entry: LeaderboardEntry | None = None
        if current_user_id is not None:
            me_stmt = select(ranked_sq).where(ranked_sq.c.user_id == current_user_id)
            me_row = (await self.db.execute(me_stmt)).first()
            if me_row is not None:
                current_user_entry = self._row_to_entry(me_row, exam_type)

        logger.info(
            f"Fetched leaderboard for exam_type={exam_type}, mode={exam_mode}, "
            f"page={page}, total={total}"
        )
        return ReturnType[LeaderboardResponse](
            success=True,
            message="Leaderboard retrieved successfully",
            data=LeaderboardResponse(
                exam_type=exam_type.strip().lower(),
                type=exam_mode.strip().lower() if exam_mode else None,
                entries=entries,
                current_user=current_user_entry,
            ),
            pagination=Pagination(total=total, page=page, per_page=limit),
        )

    async def get_user_rank(
        self,
        user_id: uuid.UUID,
        exam_type: str,
        exam_mode: str | None = None,
    ) -> ReturnType[LeaderboardEntry | None]:
        ranked_sq = self._build_ranked_subquery(exam_type=exam_type, exam_mode=exam_mode)
        stmt = select(ranked_sq).where(ranked_sq.c.user_id == user_id)
        row = (await self.db.execute(stmt)).first()

        entry = self._row_to_entry(row, exam_type) if row is not None else None
        return ReturnType[LeaderboardEntry | None](
            success=True,
            message=(
                "User leaderboard rank retrieved successfully"
                if entry
                else "User has no ranked examinations for this exam type yet"
            ),
            data=entry,
        )


def get_leaderboard_service(db: AsyncSession = Depends(get_db)) -> LeaderboardService:
    return LeaderboardService(db)
