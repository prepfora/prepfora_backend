from uuid import UUID
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from common.classes.return_type import ReturnType
from common.database import get_db
from common.exceptions.forbidden_exception import ForbiddenException
from common.services.auth import verify_access_token
from models.admin_model import Admin
from modules.analytics.schema import AdminAnalyticsResponse
from modules.analytics.service import AnalyticsService, get_analytics_service


async def require_admin_access(
    auth_data: dict = Depends(verify_access_token),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Ensures only authorized admins can access this endpoint.
    Checks:
      1. JWT payload claims: role in ['admin', 'superadmin'] or is_admin is True.
      2. OR user ID matches an active admin record in the Admin database table.
    """
    role = str(auth_data.get("role", "")).lower()
    is_admin_claim = auth_data.get("is_admin")

    if role in ["admin", "superadmin"] or is_admin_claim is True:
        return auth_data

    sub = auth_data.get("sub")
    if sub:
        try:
            admin_uuid = UUID(str(sub))
            stmt = select(Admin).where(
                Admin.id == admin_uuid,
                Admin.is_active == True,
                Admin.isDeleted == False,
            )
            result = await db.execute(stmt)
            admin_record = result.scalar_one_or_none()
            if admin_record:
                return auth_data
        except (ValueError, TypeError):
            pass

    raise ForbiddenException("Access denied. Admin privileges required.")


router = APIRouter(
    prefix="/analytics",
    tags=["Analytics"],
    responses={403: {"description": "Forbidden"}},
)


@router.get("/dashboard", response_model=ReturnType[AdminAnalyticsResponse], status_code=200)
@router.get("/admin", response_model=ReturnType[AdminAnalyticsResponse], status_code=200)
@router.get("", response_model=ReturnType[AdminAnalyticsResponse], status_code=200)
async def get_analytics_dashboard(
    _admin: dict = Depends(require_admin_access),
    service: AnalyticsService = Depends(get_analytics_service),
) -> ReturnType[AdminAnalyticsResponse]:
    return await service.get_dashboard_metrics()
