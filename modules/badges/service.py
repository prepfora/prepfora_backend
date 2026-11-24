from datetime import date, datetime, timedelta, timezone
import uuid
from fastapi import Depends
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from common.classes.return_type import Pagination, ReturnType
from common.database import get_db
from common.exceptions.bad_request_exception import BadRequestException
from common.exceptions.not_found_expection import NotFoundException
from common.logger import logger
from models.badge_model import Badge
from models.examination_model import Examination
from models.user_badge_model import UserBadge
from models.user_model import User
from modules.badges.schema import (
    BadgeResponse,
    CreateBadge,
    UpdateBadge,
    UserBadgeDetailResponse,
)


class BadgeCode:
    PROFILE_COMPLETE = "profile_complete"
    FIRST_PRACTICE = "first_practice"
    FIVE_PRACTICES = "five_practices"
    MOCK_300_CLUB = "mock_300_club"
    TEN_DAY_STREAK = "ten_day_streak"


DEFAULT_BADGES: list[dict] = [
    {
        "code": BadgeCode.PROFILE_COMPLETE,
        "title": "Profile Pioneer",
        "description": "Signed up and successfully set up your profile.",
        "image": "",
        "points_required": 0,
        "is_active": True,
    },
    {
        "code": BadgeCode.FIRST_PRACTICE,
        "title": "First Practice",
        "description": "Completed your first practice exercise.",
        "image": "",
        "points_required": 0,
        "is_active": True,
    },
    {
        "code": BadgeCode.FIVE_PRACTICES,
        "title": "Practice Pro",
        "description": "Completed 5 practice exercises.",
        "image": "",
        "points_required": 0,
        "is_active": True,
    },
    {
        "code": BadgeCode.MOCK_300_CLUB,
        "title": "300+ Mock Champion",
        "description": "Scored 300 or higher in a mock examination.",
        "image": "",
        "points_required": 300,
        "is_active": True,
    },
    {
        "code": BadgeCode.TEN_DAY_STREAK,
        "title": "10-Day Consistency Streak",
        "description": "Submitted a practice or mock exam for 10 consecutive days.",
        "image": "",
        "points_required": 0,
        "is_active": True,
    },
]


def is_profile_complete(user: User) -> bool:
    """Checks whether the user has signed up and completed all core profile fields."""
    required_strings = [
        user.email,
        user.first_name,
        user.last_name,
        user.phone,
        user.state,
        user.university,
        user.current_expectation,
        user.current_examination_date,
    ]
    if not all(isinstance(val, str) and val.strip() != "" for val in required_strings):
        return False
    if not user.examinations or len(user.examinations) == 0:
        return False
    return True


def has_consecutive_days_streak(dates: set[date], required_days: int = 10) -> bool:
    """Returns True if the set of dates contains at least `required_days` consecutive calendar days."""
    if len(dates) < required_days:
        return False
    sorted_dates = sorted(dates)
    streak = 1
    for i in range(1, len(sorted_dates)):
        if sorted_dates[i] - sorted_dates[i - 1] == timedelta(days=1):
            streak += 1
            if streak >= required_days:
                return True
        else:
            streak = 1
    return streak >= required_days


class BadgeService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def seed_default_badges(self) -> list[Badge]:
        """Idempotently creates the 5 default platform badges if they do not exist."""
        created_or_existing: list[Badge] = []
        changed = False

        for spec in DEFAULT_BADGES:
            stmt = select(Badge).where(
                or_(Badge.code == spec["code"], Badge.title == spec["title"]),
                Badge.isDeleted == False,
            )
            res = await self.db.execute(stmt)
            badge = res.scalars().first()
            if badge is None:
                badge = Badge(
                    code=spec["code"],
                    title=spec["title"],
                    description=spec["description"],
                    image=spec["image"],
                    points_required=spec["points_required"],
                    is_active=spec["is_active"],
                )
                self.db.add(badge)
                changed = True
            elif badge.code is None:
                badge.code = spec["code"]
                changed = True
            created_or_existing.append(badge)

        if changed:
            await self.db.commit()
            for badge in created_or_existing:
                await self.db.refresh(badge)

        return created_or_existing

    async def _get_or_create_badge_by_code(self, code: str) -> Badge | None:
        stmt = select(Badge).where(
            Badge.code == code,
            Badge.isDeleted == False,
            Badge.is_active == True,
        )
        res = await self.db.execute(stmt)
        badge = res.scalars().first()
        if badge:
            return badge

        # Ensure default badges are seeded if missing
        for spec in DEFAULT_BADGES:
            if spec["code"] == code:
                await self.seed_default_badges()
                res = await self.db.execute(stmt)
                return res.scalars().first()
        return None

    async def award_badge_by_code(
        self, user_id: uuid.UUID, code: str, commit: bool = True
    ) -> Badge | None:
        """Awards a badge to a user if they have not already earned it. Returns the Badge if newly awarded."""
        badge = await self._get_or_create_badge_by_code(code)
        if not badge:
            return None

        existing_stmt = select(UserBadge).where(
            UserBadge.user_id == user_id,
            UserBadge.badge_id == badge.id,
        )
        existing_res = await self.db.execute(existing_stmt)
        existing = existing_res.scalars().first()

        if existing:
            if existing.isDeleted:
                existing.isDeleted = False
                existing.deleted_at = None
                if commit:
                    await self.db.commit()
                logger.info(f"Re-awarded badge '{badge.code}' to user {user_id}")
                return badge
            return None

        user_badge = UserBadge(user_id=user_id, badge_id=badge.id)
        self.db.add(user_badge)
        if commit:
            await self.db.commit()
        logger.info(f"Awarded badge '{badge.code}' ({badge.title}) to user {user_id}")
        return badge

    async def check_and_award_profile_badge(self, user: User) -> list[Badge]:
        """Awards the profile setup badge if the user's profile is complete."""
        newly_awarded: list[Badge] = []
        if is_profile_complete(user):
            badge = await self.award_badge_by_code(user.id, BadgeCode.PROFILE_COMPLETE)
            if badge:
                newly_awarded.append(badge)
        return newly_awarded

    async def check_and_award_exam_badges(self, user_id: uuid.UUID) -> list[Badge]:
        """
        Evaluates all examination-related badge conditions for a user:
        1. Completed first practice exercise -> FIRST_PRACTICE
        2. Practiced up to 5 times -> FIVE_PRACTICES
        3. Scored up to 300 in mock exams -> MOCK_300_CLUB
        4. 10 consecutive days submitting either practice or mock -> TEN_DAY_STREAK
        """
        newly_awarded: list[Badge] = []

        # 1 & 2. Count completed practice examinations
        practice_count_stmt = (
            select(func.count(Examination.id))
            .where(
                Examination.user_id == user_id,
                Examination.isDeleted == False,
                Examination.is_completed == True,
                func.lower(Examination.type) == "practice",
            )
        )
        practice_count = (await self.db.execute(practice_count_stmt)).scalar() or 0

        if practice_count >= 1:
            b = await self.award_badge_by_code(user_id, BadgeCode.FIRST_PRACTICE, commit=False)
            if b:
                newly_awarded.append(b)

        if practice_count >= 5:
            b = await self.award_badge_by_code(user_id, BadgeCode.FIVE_PRACTICES, commit=False)
            if b:
                newly_awarded.append(b)

        # 3. Mock exam score >= 300
        mock_300_stmt = (
            select(Examination.id)
            .where(
                Examination.user_id == user_id,
                Examination.isDeleted == False,
                func.lower(Examination.type) == "mock",
                or_(Examination.score >= 300, Examination.total_score >= 300),
            )
            .limit(1)
        )
        mock_300 = (await self.db.execute(mock_300_stmt)).scalars().first()
        if mock_300 is not None:
            b = await self.award_badge_by_code(user_id, BadgeCode.MOCK_300_CLUB, commit=False)
            if b:
                newly_awarded.append(b)

        # 4. 10 consecutive days submitting either practice or mock
        streak_stmt = select(
            Examination.completed_at,
            Examination.updated_at,
            Examination.created_at,
        ).where(
            Examination.user_id == user_id,
            Examination.isDeleted == False,
            Examination.is_completed == True,
            func.lower(Examination.type).in_(["practice", "mock"]),
        )
        streak_rows = (await self.db.execute(streak_stmt)).all()
        active_dates: set[date] = set()
        for completed_at, updated_at, created_at in streak_rows:
            ts: datetime | None = completed_at or updated_at or created_at
            if ts is not None:
                if ts.tzinfo is not None:
                    ts = ts.astimezone(timezone.utc)
                active_dates.add(ts.date())

        if has_consecutive_days_streak(active_dates, required_days=10):
            b = await self.award_badge_by_code(user_id, BadgeCode.TEN_DAY_STREAK, commit=False)
            if b:
                newly_awarded.append(b)

        if newly_awarded:
            await self.db.commit()

        return newly_awarded

    async def evaluate_all_badges_for_user(
        self, user_id: uuid.UUID
    ) -> ReturnType[list[BadgeResponse]]:
        user_stmt = select(User).where(User.id == user_id, User.isDeleted == False)
        user = (await self.db.execute(user_stmt)).scalars().first()
        if not user:
            raise NotFoundException(f"User with id {user_id} not found")

        awarded: list[Badge] = []
        awarded.extend(await self.check_and_award_profile_badge(user))
        awarded.extend(await self.check_and_award_exam_badges(user.id))

        return ReturnType[list[BadgeResponse]](
            success=True,
            message=(
                f"Evaluated badges: {len(awarded)} new badge(s) awarded"
                if awarded
                else "Evaluated badges: no new badges earned"
            ),
            data=[BadgeResponse.model_validate(b) for b in awarded],
        )

    # --- CRUD & Query methods ---

    async def create_badge(self, body: CreateBadge) -> ReturnType[BadgeResponse]:
        existing_stmt = select(Badge).where(
            or_(
                Badge.title == body.title.strip(),
                (Badge.code == body.code.strip()) if body.code else False,
            ),
            Badge.isDeleted == False,
        )
        existing = (await self.db.execute(existing_stmt)).scalars().first()
        if existing:
            raise BadRequestException("A badge with this title or code already exists")

        badge = Badge(
            code=body.code.strip() if body.code else None,
            title=body.title.strip(),
            description=body.description.strip(),
            image=body.image,
            points_required=body.points_required,
            is_active=body.is_active,
        )
        self.db.add(badge)
        await self.db.commit()
        await self.db.refresh(badge)

        return ReturnType[BadgeResponse](
            success=True,
            message="Badge created successfully",
            data=BadgeResponse.model_validate(badge),
        )

    async def get_all_badges(
        self, page: int = 1, limit: int = 20, active_only: bool = True
    ) -> ReturnType[list[BadgeResponse]]:
        filters = [Badge.isDeleted == False]
        if active_only:
            filters.append(Badge.is_active == True)

        total_stmt = select(func.count(Badge.id)).where(*filters)
        total = (await self.db.execute(total_stmt)).scalar() or 0

        stmt = (
            select(Badge)
            .where(*filters)
            .order_by(Badge.created_at.asc())
            .offset((page - 1) * limit)
            .limit(limit)
        )
        badges = list((await self.db.execute(stmt)).scalars().all())

        return ReturnType[list[BadgeResponse]](
            success=True,
            message="Badges retrieved successfully",
            data=[BadgeResponse.model_validate(b) for b in badges],
            pagination=Pagination(total=total, page=page, per_page=limit),
        )

    async def get_badge_by_id(self, badge_id: uuid.UUID) -> ReturnType[BadgeResponse]:
        stmt = select(Badge).where(Badge.id == badge_id, Badge.isDeleted == False)
        badge = (await self.db.execute(stmt)).scalars().first()
        if not badge:
            raise NotFoundException(f"Badge with id {badge_id} not found")

        return ReturnType[BadgeResponse](
            success=True,
            message="Badge retrieved successfully",
            data=BadgeResponse.model_validate(badge),
        )

    async def update_badge(
        self, badge_id: uuid.UUID, body: UpdateBadge
    ) -> ReturnType[BadgeResponse]:
        stmt = select(Badge).where(Badge.id == badge_id, Badge.isDeleted == False)
        badge = (await self.db.execute(stmt)).scalars().first()
        if not badge:
            raise NotFoundException(f"Badge with id {badge_id} not found")

        if body.code is not None:
            badge.code = body.code.strip()
        if body.title is not None:
            badge.title = body.title.strip()
        if body.description is not None:
            badge.description = body.description.strip()
        if body.image is not None:
            badge.image = body.image
        if body.points_required is not None:
            badge.points_required = body.points_required
        if body.is_active is not None:
            badge.is_active = body.is_active

        await self.db.commit()
        await self.db.refresh(badge)

        return ReturnType[BadgeResponse](
            success=True,
            message="Badge updated successfully",
            data=BadgeResponse.model_validate(badge),
        )

    async def delete_badge(self, badge_id: uuid.UUID) -> ReturnType[BadgeResponse]:
        stmt = select(Badge).where(Badge.id == badge_id, Badge.isDeleted == False)
        badge = (await self.db.execute(stmt)).scalars().first()
        if not badge:
            raise NotFoundException(f"Badge with id {badge_id} not found")

        badge.isDeleted = True
        badge.deleted_at = datetime.now(timezone.utc)
        await self.db.commit()
        await self.db.refresh(badge)

        return ReturnType[BadgeResponse](
            success=True,
            message="Badge deleted successfully",
            data=BadgeResponse.model_validate(badge),
        )

    async def get_user_badges(
        self, user_id: uuid.UUID
    ) -> ReturnType[list[UserBadgeDetailResponse]]:
        stmt = (
            select(UserBadge, Badge)
            .join(Badge, UserBadge.badge_id == Badge.id)
            .where(
                UserBadge.user_id == user_id,
                UserBadge.isDeleted == False,
                Badge.isDeleted == False,
            )
            .order_by(UserBadge.created_at.desc())
        )
        rows = (await self.db.execute(stmt)).all()
        items = [
            UserBadgeDetailResponse(
                badge=BadgeResponse.model_validate(badge),
                earned_at=user_badge.created_at,
            )
            for user_badge, badge in rows
        ]

        return ReturnType[list[UserBadgeDetailResponse]](
            success=True,
            message="User badges retrieved successfully",
            data=items,
        )


def get_badge_service(db: AsyncSession = Depends(get_db)) -> BadgeService:
    return BadgeService(db)
