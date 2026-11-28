from datetime import datetime, timedelta, timezone
from uuid import UUID
from fastapi import Depends
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from common.classes.return_type import ReturnType
from common.database import get_db
from common.exceptions.bad_request_exception import BadRequestException
from common.exceptions.internal_server_exception import InternalServerException
from common.logger import logger
from models.activity_model import Activity
from models.answer_model import Answer
from models.examination_model import Examination
from models.question_model import Question
from models.user_badge_model import UserBadge
from models.user_model import User
from modules.analytics.schema import (
    ActiveStudentsMetrics,
    AdminAnalyticsResponse,
    DailyTrendPoint,
    ExamBreakdown,
    ExamTypeGlobalPerformance,
    GlobalExamPerformanceResponse,
    GlobalSubjectPerformance,
    SignupsBreakdown,
    StudentActivityMetrics,
)
from modules.questions.service import canonicalize_subject


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

    async def get_global_exam_performance(
        self,
        exam_type: str | None = None,
        exam_mode: str | None = None,
        subject: str | None = None,
    ) -> ReturnType[GlobalExamPerformanceResponse]:
        """Computes global performance across all users for JAMB and NECO, broken down by subject."""
        target_groups: list[str]
        if exam_type and exam_type.strip():
            et_clean = exam_type.strip().lower()
            if et_clean in ("jamb", "utme"):
                target_groups = ["jamb"]
            elif et_clean == "neco":
                target_groups = ["neco"]
            else:
                raise BadRequestException(
                    f"Unsupported exam_type '{exam_type}'. Must be 'jamb', 'utme', or 'neco'."
                )
        else:
            target_groups = ["jamb", "neco"]

        allowed_raw_types: list[str] = []
        if "jamb" in target_groups:
            allowed_raw_types.extend(["jamb", "utme"])
        if "neco" in target_groups:
            allowed_raw_types.append("neco")

        subject_filter_canonical = canonicalize_subject(subject) if (subject and subject.strip()) else None

        exam_filters = [
            Examination.isDeleted == False,
            func.lower(Examination.exam_type).in_(allowed_raw_types),
        ]
        if exam_mode and exam_mode.strip():
            exam_filters.append(func.lower(Examination.type) == exam_mode.strip().lower())

        exams_stmt = select(Examination).where(*exam_filters)
        examinations = list((await self.db.execute(exams_stmt)).scalars().all())

        exam_ids = [e.id for e in examinations]
        answers_by_exam: dict[UUID, list[Answer]] = {}
        all_qids: set[int] = set()

        if exam_ids:
            ans_stmt = select(Answer).where(
                Answer.examination_id.in_(exam_ids),
                Answer.isDeleted == False,
            )
            answers = list((await self.db.execute(ans_stmt)).scalars().all())
            for ans in answers:
                answers_by_exam.setdefault(ans.examination_id, []).append(ans)
                all_qids.add(ans.question_id)

        for exam in examinations:
            for qid in (exam.questions_ids or []):
                all_qids.add(qid)
            for raw_list in (exam.correct_questions, exam.failed_questions):
                for qid_str in (raw_list or []):
                    try:
                        all_qids.add(int(qid_str))
                    except (ValueError, TypeError):
                        continue

        q_subject_by_id: dict[int, str] = {}
        if all_qids:
            q_id_list = list(all_qids)
            q_stmt = select(Question.id, Question.external_id, Question.subject, Question.category).where(
                or_(Question.id.in_(q_id_list), Question.external_id.in_(q_id_list)),
                Question.isDeleted == False,
            )
            for q_id, q_ext_id, q_subj, q_cat in (await self.db.execute(q_stmt)).all():
                raw_s = (q_subj or q_cat or "").strip()
                if raw_s:
                    canon = canonicalize_subject(raw_s)
                    q_subject_by_id[q_id] = canon
                    if q_ext_id is not None and q_ext_id not in q_subject_by_id:
                        q_subject_by_id[q_ext_id] = canon

        # Structure: group -> canonical_subject -> stats
        group_data: dict[str, dict] = {
            grp: {
                "exam_ids": set(),
                "user_ids": set(),
                "subjects": {},
            }
            for grp in target_groups
        }

        for exam in examinations:
            raw_et = (exam.exam_type or "").strip().lower()
            grp = "jamb" if raw_et in ("jamb", "utme") else "neco"
            if grp not in group_data:
                continue

            exam_subjects = [canonicalize_subject(s) for s in (exam.subjects or []) if s and s.strip()]
            fallback_subj = exam_subjects[0] if len(exam_subjects) == 1 else None

            # Track per-exam per-subject counts for accurate average_score_percentage
            per_exam_subj: dict[str, dict[str, int]] = {}

            def ensure_subj(s_name: str) -> dict[str, int]:
                if s_name not in per_exam_subj:
                    per_exam_subj[s_name] = {"total": 0, "correct": 0, "failed": 0}
                return per_exam_subj[s_name]

            for qid in (exam.questions_ids or []):
                s_name = q_subject_by_id.get(qid) or fallback_subj
                if s_name:
                    ensure_subj(s_name)["total"] += 1

            exam_answers = answers_by_exam.get(exam.id, [])
            if exam_answers:
                for ans in exam_answers:
                    s_name = q_subject_by_id.get(ans.question_id) or fallback_subj
                    if not s_name:
                        continue
                    bucket = ensure_subj(s_name)
                    if (
                        ans.picked_answer is not None
                        and ans.correct_answer is not None
                        and ans.picked_answer.strip().lower() == ans.correct_answer.strip().lower()
                    ):
                        bucket["correct"] += 1
                    else:
                        bucket["failed"] += 1
            else:
                for qid_str in (exam.correct_questions or []):
                    try:
                        qid = int(qid_str)
                    except (ValueError, TypeError):
                        continue
                    s_name = q_subject_by_id.get(qid) or fallback_subj
                    if s_name:
                        ensure_subj(s_name)["correct"] += 1

                for qid_str in (exam.failed_questions or []):
                    try:
                        qid = int(qid_str)
                    except (ValueError, TypeError):
                        continue
                    s_name = q_subject_by_id.get(qid) or fallback_subj
                    if s_name:
                        ensure_subj(s_name)["failed"] += 1

            # Include declared exam subjects even if 0 questions were answered
            for s_name in exam_subjects:
                ensure_subj(s_name)

            group_matched = False
            for s_name, counts in per_exam_subj.items():
                if subject_filter_canonical and s_name != subject_filter_canonical:
                    continue
                group_matched = True
                subj_map = group_data[grp]["subjects"]
                if s_name not in subj_map:
                    subj_map[s_name] = {
                        "exam_ids": set(),
                        "user_ids": set(),
                        "correct": 0,
                        "failed": 0,
                        "exam_score_pcts": [],
                    }
                entry = subj_map[s_name]
                entry["exam_ids"].add(exam.id)
                entry["user_ids"].add(exam.user_id)
                entry["correct"] += counts["correct"]
                entry["failed"] += counts["failed"]

                attempted = counts["correct"] + counts["failed"]
                if attempted > 0:
                    denom = counts["total"] if counts["total"] >= attempted else attempted
                    entry["exam_score_pcts"].append((counts["correct"] / denom) * 100.0)

            if group_matched:
                group_data[grp]["exam_ids"].add(exam.id)
                group_data[grp]["user_ids"].add(exam.user_id)

        def build_group_response(grp_name: str) -> ExamTypeGlobalPerformance | None:
            if grp_name not in group_data:
                return None
            gd = group_data[grp_name]
            subject_list: list[GlobalSubjectPerformance] = []
            grp_correct = 0
            grp_failed = 0

            for s_name, entry in gd["subjects"].items():
                c = entry["correct"]
                f = entry["failed"]
                att = c + f
                grp_correct += c
                grp_failed += f
                acc = round((c / att) * 100.0, 2) if att > 0 else 0.0
                pcts = entry["exam_score_pcts"]
                avg_pct = round(sum(pcts) / len(pcts), 2) if pcts else 0.0

                subject_list.append(
                    GlobalSubjectPerformance(
                        subject=s_name,
                        total_examinations=len(entry["exam_ids"]),
                        total_students=len(entry["user_ids"]),
                        total_questions_attempted=att,
                        total_correct=c,
                        total_failed=f,
                        accuracy_percentage=acc,
                        average_score_percentage=avg_pct,
                    )
                )

            subject_list.sort(key=lambda x: (-x.total_questions_attempted, x.subject))
            grp_attempted = grp_correct + grp_failed
            grp_acc = round((grp_correct / grp_attempted) * 100.0, 2) if grp_attempted > 0 else 0.0

            return ExamTypeGlobalPerformance(
                exam_type=grp_name,
                total_examinations=len(gd["exam_ids"]),
                total_students=len(gd["user_ids"]),
                total_questions_attempted=grp_attempted,
                total_correct=grp_correct,
                total_failed=grp_failed,
                overall_accuracy_percentage=grp_acc,
                subjects=subject_list,
            )

        return ReturnType[GlobalExamPerformanceResponse](
            success=True,
            message="Global exam performance retrieved successfully",
            data=GlobalExamPerformanceResponse(
                jamb=build_group_response("jamb"),
                neco=build_group_response("neco"),
            ),
        )


def get_analytics_service(db: AsyncSession = Depends(get_db)) -> AnalyticsService:
    return AnalyticsService(db)
