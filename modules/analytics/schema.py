from pydantic import BaseModel, Field
from typing import Dict, List


class ActiveStudentsMetrics(BaseModel):
    daily_active: int = Field(description="Students active in the last 24 hours")
    weekly_active: int = Field(description="Students active in the last 7 days")
    monthly_active: int = Field(description="Students active in the last 30 days")


class SignupsBreakdown(BaseModel):
    today: int = Field(description="New sign-ups in the last 24 hours")
    this_week: int = Field(description="New sign-ups in the last 7 days")
    this_month: int = Field(description="New sign-ups in the last 30 days")
    total: int = Field(description="Total registered students all-time")


class ExamBreakdown(BaseModel):
    total_taken: int = Field(description="Total practices and exams taken")
    practices_taken: int = Field(description="Total practice sessions taken")
    mocks_taken: int = Field(description="Total mock exams taken")
    taken_today: int = Field(description="Exams taken in the last 24 hours")
    taken_this_week: int = Field(description="Exams taken in the last 7 days")
    taken_this_month: int = Field(description="Exams taken in the last 30 days")
    by_exam_type: Dict[str, int] = Field(
        default_factory=dict,
        description="Breakdown by exam category (e.g., WAEC, UTME, NECO, JAMB)",
    )


class StudentActivityMetrics(BaseModel):
    total_activities_logged: int = Field(description="Total activities recorded in the system")
    total_questions_answered: int = Field(description="Total questions answered across all sessions")
    total_questions_failed: int = Field(description="Total questions answered incorrectly")
    total_questions_correct: int = Field(description="Total questions answered correctly")
    accuracy_rate_percentage: float = Field(description="Overall student accuracy percentage")
    average_exam_score: float = Field(description="Average score across completed exams")
    total_prep_points_awarded: int = Field(description="Total prep points accumulated across students")
    total_badges_earned: int = Field(description="Total badges earned by students")


class DailyTrendPoint(BaseModel):
    date: str = Field(description="Date in YYYY-MM-DD format")
    signups: int = Field(description="Sign-ups on this day")
    exams_taken: int = Field(description="Exams taken on this day")


class AdminAnalyticsResponse(BaseModel):
    total_students: int = Field(description="Total number of students")
    active_students: ActiveStudentsMetrics = Field(description="Active student statistics across timeframes")
    new_signups: SignupsBreakdown = Field(description="New student sign-ups breakdown")
    exams_and_practices: ExamBreakdown = Field(description="Practices and examinations analytics")
    activity_metrics: StudentActivityMetrics = Field(description="Key student activity and performance metrics")
    recent_trends_7d: List[DailyTrendPoint] = Field(
        default_factory=list,
        description="7-day daily activity trends for dashboard visualisations",
    )


class GlobalSubjectPerformance(BaseModel):
    subject: str = Field(description="Canonical subject name")
    total_examinations: int = Field(description="Number of examinations that included this subject")
    total_students: int = Field(description="Number of unique students who attempted this subject")
    total_questions_attempted: int = Field(description="Total questions answered in this subject")
    total_correct: int = Field(description="Total questions answered correctly")
    total_failed: int = Field(description="Total questions answered incorrectly")
    accuracy_percentage: float = Field(description="Overall accuracy percentage (0-100)")
    average_score_percentage: float = Field(description="Average per-exam score percentage (0-100)")


class ExamTypeGlobalPerformance(BaseModel):
    exam_type: str = Field(description="Examination type (jamb or neco)")
    total_examinations: int = Field(description="Total examinations taken for this exam type")
    total_students: int = Field(description="Unique students who took this exam type")
    total_questions_attempted: int = Field(description="Total questions attempted across all subjects")
    total_correct: int = Field(description="Total correct answers across all subjects")
    total_failed: int = Field(description="Total failed answers across all subjects")
    overall_accuracy_percentage: float = Field(description="Overall accuracy percentage across all subjects")
    subjects: List[GlobalSubjectPerformance] = Field(
        default_factory=list,
        description="Performance breakdown per subject",
    )


class GlobalExamPerformanceResponse(BaseModel):
    jamb: ExamTypeGlobalPerformance | None = Field(
        default=None,
        description="Global performance for JAMB/UTME examinations per subject",
    )
    neco: ExamTypeGlobalPerformance | None = Field(
        default=None,
        description="Global performance for NECO examinations per subject",
    )
