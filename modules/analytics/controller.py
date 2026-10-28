from uuid import UUID
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from common.classes.return_type import ReturnType
from common.database import get_db
from common.exceptions.forbidden_exception import ForbiddenException
from common.services.auth import verify_access_token
from models.admin_model import Admin
from modules.affiliate.schema import AffiliateAnalyticsResponse, ReferredUserResponse
from modules.affiliate.service import AffiliateService, get_affiliate_service
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


@router.get("/affiliate", response_model=ReturnType[AffiliateAnalyticsResponse], status_code=200)
@router.get("/affiliate/referrals", response_model=ReturnType[AffiliateAnalyticsResponse], status_code=200)
async def get_affiliate_analytics_in_analytics(
    affiliate_id: UUID | None = Query(
        None,
        description="Optional affiliate ID (admin only to view a specific affiliate; authenticated affiliates view their own stats automatically)",
    ),
    auth_data: dict = Depends(verify_access_token),
    service: AffiliateService = Depends(get_affiliate_service),
) -> ReturnType[AffiliateAnalyticsResponse]:
    """
    Analytics endpoint for affiliates to get the total number of users that they have referred.
    """
    return await service.get_affiliate_referral_analytics(auth_data=auth_data, affiliate_id=affiliate_id)


@router.get("/affiliate/users", response_model=ReturnType[list[ReferredUserResponse]], status_code=200)
@router.get("/affiliate/referrals/users", response_model=ReturnType[list[ReferredUserResponse]], status_code=200)
async def get_affiliate_referred_users_in_analytics(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    search: str | None = Query(None, description="Optional search by name, email, or phone"),
    affiliate_id: UUID | None = Query(
        None,
        description="Optional affiliate ID (admin only to view a specific affiliate; authenticated affiliates view their own users automatically)",
    ),
    auth_data: dict = Depends(verify_access_token),
    service: AffiliateService = Depends(get_affiliate_service),
) -> ReturnType[list[ReferredUserResponse]]:
    """
    Retrieves a paginated list of users referred by the affiliate.
    """
    return await service.get_referred_users(
        auth_data=auth_data,
        affiliate_id=affiliate_id,
        page=page,
        limit=limit,
        search=search,
    )
