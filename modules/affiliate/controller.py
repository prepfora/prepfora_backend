from uuid import UUID
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from common.classes.return_type import ReturnType
from common.database import get_db
from common.exceptions.api_exception import APIException
from common.exceptions.bad_request_exception import BadRequestException
from common.exceptions.forbidden_exception import ForbiddenException
from common.logger import logger
from common.services.auth import verify_access_token
from models.admin_model import Admin
from modules.affiliate.schema import (
    AffiliateAuthResponse,
    AffiliateLoginRequest,
    AffiliateRefreshTokenRequest,
    AffiliateRegisterRequest,
    AffiliateResponse,
    AffiliateTokenData,
    AffiliateValidateOtpRequest,
    InviteResponse,
    MessageResponse,
    SendInviteRequest,
)
from modules.affiliate.service import AffiliateService, get_affiliate_service


async def require_admin_access(
    auth_data: dict = Depends(verify_access_token),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Ensures only authorized admins can access admin-restricted endpoints.
    Checks:
      1. JWT payload claims: role in ['admin', 'superadmin', 'super admin'] or is_admin is True.
      2. OR user ID matches an active admin record in the Admin database table.
    """
    role = str(auth_data.get("role", "")).lower()
    is_admin_claim = auth_data.get("is_admin")

    if role in ["admin", "superadmin", "super admin"] or is_admin_claim is True:
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
    prefix="/affiliate",
    tags=["Affiliate"],
)


# 1. Admin-only: Send invite to affiliate
@router.post("/invite", response_model=ReturnType[InviteResponse], status_code=201)
@router.post("/admin/invite", response_model=ReturnType[InviteResponse], status_code=201)
async def send_invite(
    payload: SendInviteRequest,
    _admin: dict = Depends(require_admin_access),
    service: AffiliateService = Depends(get_affiliate_service),
) -> ReturnType[InviteResponse]:
    """
    Admin-only endpoint to send an affiliate invitation.
    Generates a unique 6-digit invite code (expires in 24 hours) and emails the joining link to the affiliate.
    """
    try:
        return await service.send_invite(payload)
    except APIException:
        raise
    except Exception as e:
        logger.error(f"Failed to send affiliate invite: {e}")
        raise BadRequestException(str(e))


# 5. Affiliate Registration (verifies 6-digit invite code & deactivates invite)
@router.post("/register", response_model=ReturnType[AffiliateAuthResponse], status_code=201)
@router.post("/auth/register", response_model=ReturnType[AffiliateAuthResponse], status_code=201)
async def register_affiliate(
    payload: AffiliateRegisterRequest,
    service: AffiliateService = Depends(get_affiliate_service),
) -> ReturnType[AffiliateAuthResponse]:
    """
    Registers a new affiliate account after verifying their 6-digit invite code.
    Upon verification, the invite is marked as not active (isActive=False).
    """
    try:
        return await service.register_affiliate(payload)
    except APIException:
        raise
    except Exception as e:
        logger.error(f"Failed to register affiliate: {e}")
        raise BadRequestException(str(e))


# 2a. Affiliate Login (sends 6-digit OTP to email, or verifies if OTP is provided)
@router.post("/login", response_model=ReturnType[MessageResponse | AffiliateAuthResponse], status_code=200)
@router.post("/auth/login", response_model=ReturnType[MessageResponse | AffiliateAuthResponse], status_code=200)
async def login_affiliate(
    payload: AffiliateLoginRequest,
    service: AffiliateService = Depends(get_affiliate_service),
) -> ReturnType[MessageResponse | AffiliateAuthResponse]:
    """
    Initiates passwordless affiliate login by sending a 6-digit OTP code to their email.
    If `otp` is also provided in the request body, verifies it immediately and returns tokens and affiliate details.
    """
    try:
        return await service.login_affiliate(payload)
    except APIException:
        raise
    except Exception as e:
        logger.error(f"Failed to login affiliate: {e}")
        raise BadRequestException(str(e))


# 2b. Verify Affiliate Login OTP (returns access_token, refresh_token, and affiliate details)
@router.post("/validate-otp", response_model=ReturnType[AffiliateAuthResponse], status_code=200)
@router.post("/verify-otp", response_model=ReturnType[AffiliateAuthResponse], status_code=200)
@router.post("/auth/validate-otp", response_model=ReturnType[AffiliateAuthResponse], status_code=200)
@router.post("/auth/verify-otp", response_model=ReturnType[AffiliateAuthResponse], status_code=200)
async def validate_affiliate_otp(
    payload: AffiliateValidateOtpRequest,
    service: AffiliateService = Depends(get_affiliate_service),
) -> ReturnType[AffiliateAuthResponse]:
    """
    Verifies the 6-digit OTP sent to the affiliate's email and returns access token, refresh token, and affiliate details.
    """
    try:
        return await service.validate_otp(payload)
    except APIException:
        raise
    except Exception as e:
        logger.error(f"Failed to validate affiliate OTP: {e}")
        raise BadRequestException(str(e))


# 3. Refresh Affiliate Token
@router.post("/refresh-token", response_model=ReturnType[AffiliateTokenData], status_code=200)
@router.post("/auth/refresh-token", response_model=ReturnType[AffiliateTokenData], status_code=200)
async def refresh_affiliate_token(
    payload: AffiliateRefreshTokenRequest,
    service: AffiliateService = Depends(get_affiliate_service),
) -> ReturnType[AffiliateTokenData]:
    """Refreshes an affiliate's access and refresh tokens using a valid refresh token."""
    try:
        return await service.refresh_token(payload)
    except APIException:
        raise
    except Exception as e:
        logger.error(f"Failed to refresh affiliate token: {e}")
        raise BadRequestException(str(e))


# Current authenticated affiliate details
@router.get("/me", response_model=ReturnType[AffiliateResponse], status_code=200)
@router.get("/auth/me", response_model=ReturnType[AffiliateResponse], status_code=200)
async def get_current_affiliate_details(
    auth_data: dict = Depends(verify_access_token),
    service: AffiliateService = Depends(get_affiliate_service),
) -> ReturnType[AffiliateResponse]:
    """Gets details of the currently authenticated affiliate."""
    try:
        affiliate_id = auth_data.get("sub")
        return await service.get_affiliate_by_id(affiliate_id)
    except APIException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch current affiliate details: {e}")
        raise BadRequestException(str(e))


# Admin helper endpoints: list all affiliates and invites
@router.get("/admin/all", response_model=ReturnType[list[AffiliateResponse]], status_code=200)
async def list_all_affiliates(
    _admin: dict = Depends(require_admin_access),
    service: AffiliateService = Depends(get_affiliate_service),
) -> ReturnType[list[AffiliateResponse]]:
    """Admin-only endpoint to list all affiliates."""
    try:
        return await service.get_all_affiliates()
    except APIException:
        raise
    except Exception as e:
        logger.error(f"Failed to list affiliates: {e}")
        raise BadRequestException(str(e))


@router.get("/admin/invites", response_model=ReturnType[list[InviteResponse]], status_code=200)
async def list_all_invites(
    _admin: dict = Depends(require_admin_access),
    service: AffiliateService = Depends(get_affiliate_service),
) -> ReturnType[list[InviteResponse]]:
    """Admin-only endpoint to list all invites."""
    try:
        return await service.get_all_invites()
    except APIException:
        raise
    except Exception as e:
        logger.error(f"Failed to list invites: {e}")
        raise BadRequestException(str(e))


# 4. Get Affiliate Details by ID
@router.get("/details/{id}", response_model=ReturnType[AffiliateResponse], status_code=200)
@router.get("/{id}", response_model=ReturnType[AffiliateResponse], status_code=200)
async def get_affiliate_details_by_id(
    id: UUID,
    service: AffiliateService = Depends(get_affiliate_service),
) -> ReturnType[AffiliateResponse]:
    """Retrieves an affiliate's details by their ID."""
    try:
        return await service.get_affiliate_by_id(id)
    except APIException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch affiliate details by ID: {e}")
        raise BadRequestException(str(e))
