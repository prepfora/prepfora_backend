import uuid
from uuid import UUID
from fastapi import Depends
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from common.classes.return_type import Pagination, ReturnType
from common.database import get_db
from common.exceptions.bad_request_exception import BadRequestException
from common.exceptions.internal_server_exception import InternalServerException
from common.exceptions.not_found_expection import NotFoundException
from common.logger import logger
from models.badge_model import Badge
from models.examination_model import Examination
from models.user_badge_model import UserBadge
from models.user_model import User
from modules.user.schema import (
    UserBadgeResponse,
    UserDetailResponse,
    UserListItemResponse,
)


class UserManagementService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_all_users(
        self,
        page: int = 1,
        limit: int = 20,
        search: str | None = None,
    ) -> ReturnType[list[UserListItemResponse]]:
        """
        Retrieves a paginated list of all users on the platform.
        Supports searching across email, first name, last name, and full name.
        """
        try:
            if page < 1:
                raise BadRequestException("Page must be greater than 0")
            if limit < 1:
                raise BadRequestException("Limit must be greater than 0")

            filters = [User.isDeleted == False]

            if search and search.strip():
                clean_term = search.strip().lower()
                pattern = f"%{clean_term}%"
                full_name_expr = func.concat(
                    func.coalesce(User.first_name, ""),
                    " ",
                    func.coalesce(User.last_name, ""),
                )
                filters.append(
                    or_(
                        func.lower(User.email).like(pattern),
                        func.lower(User.first_name).like(pattern),
                        func.lower(User.last_name).like(pattern),
                        func.lower(full_name_expr).like(pattern),
                    )
                )

            # Total count
            total_stmt = select(func.count(User.id)).where(*filters)
            total = (await self.db.execute(total_stmt)).scalar() or 0

            # Users page
            users_stmt = (
                select(User)
                .where(*filters)
                .order_by(User.created_at.desc())
                .offset((page - 1) * limit)
                .limit(limit)
            )
            users = (await self.db.execute(users_stmt)).scalars().all()

            # Batch load total_exams count for users on this page
            exam_counts: dict[UUID, int] = {}
            if users:
                user_ids = [u.id for u in users]
                exam_stmt = (
                    select(Examination.user_id, func.count(Examination.id))
                    .where(
                        Examination.user_id.in_(user_ids),
                        Examination.isDeleted == False,
                    )
                    .group_by(Examination.user_id)
                )
                exam_results = (await self.db.execute(exam_stmt)).all()
                exam_counts = {uid: count for uid, count in exam_results}

            user_items = [
                UserListItemResponse(
                    id=u.id,
                    first_name=u.first_name,
                    last_name=u.last_name,
                    email=u.email,
                    phone=u.phone,
                    state=u.state,
                    university=u.university,
                    examinations=u.examinations,
                    current_expectation=u.current_expectation,
                    current_examination_date=u.current_examination_date,
                    prep_points=u.prep_points or 0,
                    best_score=u.best_score or 0,
                    profile_picture=u.profile_picture,
                    referral_code=u.referral_code,
                    total_exams=exam_counts.get(u.id, 0),
                    created_at=u.created_at,
                    updated_at=u.updated_at,
                )
                for u in users
            ]

            return ReturnType[list[UserListItemResponse]](
                success=True,
                message="Users retrieved successfully",
                data=user_items,
                pagination=Pagination(
                    total=total,
                    page=page,
                    per_page=limit,
                ),
            )

        except BadRequestException:
            raise
        except Exception as e:
            logger.error(f"Error in get_all_users: {e}")
            raise InternalServerException(str(e))

    async def get_user_by_id(self, user_id: UUID) -> ReturnType[UserDetailResponse]:
        """
        Retrieves user details by user ID along with their exam and badge statistics:
        - total exams taken
        - total mock exams taken
        - total practice exams taken
        - total badges earned (and badge list)
        """
        try:
            # 1. Fetch user
            user_stmt = select(User).where(User.id == user_id, User.isDeleted == False)
            user = (await self.db.execute(user_stmt)).scalars().first()

            if user is None:
                raise NotFoundException(f"User with ID '{user_id}' not found")

            # 2. Single query for total, mock, and practice exam counts
            exam_counts_stmt = (
                select(
                    func.count(Examination.id).label("total"),
                    func.count().filter(func.lower(Examination.type) == "mock").label("mock"),
                    func.count().filter(func.lower(Examination.type) == "practice").label("practice"),
                )
                .where(
                    Examination.user_id == user_id,
                    Examination.isDeleted == False,
                )
            )
            exam_row = (await self.db.execute(exam_counts_stmt)).first()
            total_exams = exam_row.total if exam_row else 0
            total_mock_exams = exam_row.mock if exam_row else 0
            total_practice_exams = exam_row.practice if exam_row else 0

            # 3. Fetch badges earned by user
            badges_stmt = (
                select(Badge)
                .join(UserBadge, UserBadge.badge_id == Badge.id)
                .where(
                    UserBadge.user_id == user_id,
                    UserBadge.isDeleted == False,
                    Badge.isDeleted == False,
                )
            )
            badges = (await self.db.execute(badges_stmt)).scalars().all()
            total_badges = len(badges)

            response_data = UserDetailResponse(
                id=user.id,
                first_name=user.first_name,
                last_name=user.last_name,
                email=user.email,
                phone=user.phone,
                state=user.state,
                university=user.university,
                examinations=user.examinations,
                current_expectation=user.current_expectation,
                current_examination_date=user.current_examination_date,
                prep_points=user.prep_points or 0,
                best_score=user.best_score or 0,
                profile_picture=user.profile_picture,
                referral_code=user.referral_code,
                created_at=user.created_at,
                updated_at=user.updated_at,
                total_exams=total_exams,
                total_mock_exams=total_mock_exams,
                total_practice_exams=total_practice_exams,
                total_badges=total_badges,
                badges=[UserBadgeResponse.model_validate(b) for b in badges],
            )

            return ReturnType[UserDetailResponse](
                success=True,
                message="User details retrieved successfully",
                data=response_data,
            )

        except (BadRequestException, NotFoundException):
            raise
        except Exception as e:
            logger.error(f"Error in get_user_by_id: {e}")
            raise InternalServerException(str(e))


def get_user_management_service(
    db: AsyncSession = Depends(get_db),
) -> UserManagementService:
    return UserManagementService(db)
