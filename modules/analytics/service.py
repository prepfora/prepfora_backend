from datetime import datetime, timedelta, timezone
from uuid import UUID
from fastapi import Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from common.classes.return_type import ReturnType
from common.database import get_db
from common.exceptions.internal_server_exception import InternalServerException
from common.logger import logger
from models.activity_model import Activity
from models.examination_model import Examination
from models.user_badge_model import UserBadge
from models.user_model import User
from modules.analytics.schema import (
    ActiveStudentsMetrics,
    AdminAnalyticsResponse,
    DailyTrendPoint,
    ExamBreakdown,
    SignupsBreakdown,
    StudentActivityMetrics,
)


class AnalyticsService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_dashboard_metrics(self) -> ReturnType[AdminAnalyticsResponse]:
        try:
            logger.info("Computing admin analytics dashboard metrics...")
            now = datetime.now(timezone.utc)
            day_ago = now - timedelta(days=1)
            week_ago = now - timedelta(days=7)
            month_ago = now - timedelta(days=30)

            # ==========================================
            # 1. TOTAL STUDENTS
            # ==========================================
            total_students_stmt = select(func.count()).select_from(User).where(User.isDeleted == False)
            total_students_res = await self.db.execute(total_students_stmt)
            total_students = total_students_res.scalar_one()

            # ==========================================
            # 2. NEW SIGN-UPS
            # ==========================================
            signups_today_stmt = (
                select(func.count())
                .select_from(User)
                .where(User.isDeleted == False, User.created_at >= day_ago)
            )
            signups_week_stmt = (
                select(func.count())
                .select_from(User)
                .where(User.isDeleted == False, User.created_at >= week_ago)
            )
            signups_month_stmt = (
                select(func.count())
                .select_from(User)
                .where(User.isDeleted == False, User.created_at >= month_ago)
            )

            signups_today = (await self.db.execute(signups_today_stmt)).scalar_one()
            signups_week = (await self.db.execute(signups_week_stmt)).scalar_one()
            signups_month = (await self.db.execute(signups_month_stmt)).scalar_one()

            new_signups = SignupsBreakdown(
                today=signups_today,
                this_week=signups_week,
                this_month=signups_month,
                total=total_students,
            )

            # ==========================================
            # 3. ACTIVE STUDENTS (Deduplicated across Exams & Activities)
            # ==========================================
            async def get_active_count(since_time: datetime) -> int:
                exam_sub = (
                    select(Examination.user_id)
                    .where(Examination.isDeleted == False, Examination.created_at >= since_time)
                )
                act_sub = (
                    select(Activity.user_id)
                    .where(Activity.isDeleted == False, Activity.created_at >= since_time)
                )
                union_sub = exam_sub.union(act_sub).subquery()
                stmt = select(func.count()).select_from(union_sub)
                res = await self.db.execute(stmt)
                return res.scalar_one()

            daily_active = await get_active_count(day_ago)
            weekly_active = await get_active_count(week_ago)
            monthly_active = await get_active_count(month_ago)

            active_metrics = ActiveStudentsMetrics(
                daily_active=daily_active,
                weekly_active=weekly_active,
                monthly_active=monthly_active,
            )

            # ==========================================
            # 4. PRACTICES AND EXAMINATIONS TAKEN
            # ==========================================
            total_exams_stmt = select(func.count()).select_from(Examination).where(Examination.isDeleted == False)
            total_exams = (await self.db.execute(total_exams_stmt)).scalar_one()

            practices_stmt = (
                select(func.count())
                .select_from(Examination)
                .where(Examination.isDeleted == False, func.lower(Examination.type) == "practice")
            )
            practices_taken = (await self.db.execute(practices_stmt)).scalar_one()

            mocks_stmt = (
                select(func.count())
                .select_from(Examination)
                .where(Examination.isDeleted == False, func.lower(Examination.type) == "mock")
            )
            mocks_taken = (await self.db.execute(mocks_stmt)).scalar_one()

            exams_today_stmt = (
                select(func.count())
                .select_from(Examination)
                .where(Examination.isDeleted == False, Examination.created_at >= day_ago)
            )
            exams_today = (await self.db.execute(exams_today_stmt)).scalar_one()

            exams_week_stmt = (
                select(func.count())
                .select_from(Examination)
                .where(Examination.isDeleted == False, Examination.created_at >= week_ago)
            )
            exams_week = (await self.db.execute(exams_week_stmt)).scalar_one()

            exams_month_stmt = (
                select(func.count())
                .select_from(Examination)
                .where(Examination.isDeleted == False, Examination.created_at >= month_ago)
            )
            exams_month = (await self.db.execute(exams_month_stmt)).scalar_one()

            # Breakdown by exam type (WAEC, UTME, NECO, etc.)
            by_type_stmt = (
                select(Examination.exam_type, func.count())
                .where(Examination.isDeleted == False)
                .group_by(Examination.exam_type)
            )
            by_type_rows = (await self.db.execute(by_type_stmt)).all()
            by_exam_type = {str(row[0]).upper(): row[1] for row in by_type_rows if row[0]}

            exam_breakdown = ExamBreakdown(
                total_taken=total_exams,
                practices_taken=practices_taken,
                mocks_taken=mocks_taken,
                taken_today=exams_today,
                taken_this_week=exams_week,
                taken_this_month=exams_month,
                by_exam_type=by_exam_type,
            )

            # ==========================================
            # 5. OTHER STUDENT ACTIVITY METRICS
            # ==========================================
            total_act_stmt = select(func.count()).select_from(Activity).where(Activity.isDeleted == False)
            total_activities = (await self.db.execute(total_act_stmt)).scalar_one()

            answered_stmt = select(
                func.coalesce(func.sum(Examination.total_questions_answered), 0),
                func.coalesce(func.sum(Examination.total_questions_failed), 0),
                func.coalesce(func.avg(Examination.total_score), 0.0),
            ).where(Examination.isDeleted == False)
            exam_stats_res = await self.db.execute(answered_stmt)
            total_answered, total_failed, avg_score = exam_stats_res.one()

            total_answered = int(total_answered or 0)
            total_failed = int(total_failed or 0)
            total_correct = max(0, total_answered - total_failed)
            accuracy_rate = round((total_correct / total_answered * 100), 2) if total_answered > 0 else 0.0

            points_stmt = select(func.coalesce(func.sum(User.prep_points), 0)).where(User.isDeleted == False)
            total_points = int((await self.db.execute(points_stmt)).scalar_one() or 0)

            badges_stmt = select(func.count()).select_from(UserBadge).where(UserBadge.isDeleted == False)
            total_badges = (await self.db.execute(badges_stmt)).scalar_one()

            activity_metrics = StudentActivityMetrics(
                total_activities_logged=total_activities,
                total_questions_answered=total_answered,
                total_questions_failed=total_failed,
                total_questions_correct=total_correct,
                accuracy_rate_percentage=accuracy_rate,
                average_exam_score=round(float(avg_score or 0.0), 2),
                total_prep_points_awarded=total_points,
                total_badges_earned=total_badges,
            )

            # ==========================================
            # 6. RECENT 7-DAY TRENDS
            # ==========================================
            recent_trends: list[DailyTrendPoint] = []
            for i in range(6, -1, -1):
                day_start = (now - timedelta(days=i)).replace(hour=0, minute=0, second=0, microsecond=0)
                day_end = day_start + timedelta(days=1)
                day_str = day_start.strftime("%Y-%m-%d")

                day_signups_stmt = select(func.count()).select_from(User).where(
                    User.isDeleted == False,
                    User.created_at >= day_start,
                    User.created_at < day_end,
                )
                day_exams_stmt = select(func.count()).select_from(Examination).where(
                    Examination.isDeleted == False,
                    Examination.created_at >= day_start,
                    Examination.created_at < day_end,
                )

                day_signups = (await self.db.execute(day_signups_stmt)).scalar_one()
                day_exams = (await self.db.execute(day_exams_stmt)).scalar_one()

                recent_trends.append(
                    DailyTrendPoint(
                        date=day_str,
                        signups=day_signups,
                        exams_taken=day_exams,
                    )
                )

            data = AdminAnalyticsResponse(
                total_students=total_students,
                active_students=active_metrics,
                new_signups=new_signups,
                exams_and_practices=exam_breakdown,
                activity_metrics=activity_metrics,
                recent_trends_7d=recent_trends,
            )

            logger.info("Admin analytics dashboard metrics successfully calculated.")
            return ReturnType[AdminAnalyticsResponse](
                success=True,
                message="Admin analytics dashboard metrics retrieved successfully",
                data=data,
            )

        except Exception as e:
            logger.error(f"Error computing admin analytics: {str(e)}")
            raise InternalServerException(f"Failed to compute analytics: {str(e)}")


def get_analytics_service(db: AsyncSession = Depends(get_db)) -> AnalyticsService:
    return AnalyticsService(db)
