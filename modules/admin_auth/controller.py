from fastapi import APIRouter, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from common.classes.return_type import ReturnType
from common.exceptions.bad_request_exception import BadRequestException
from common.exceptions.unauthorized_exception import UnauthorizedException
from common.logger import logger
from common.services.auth import verify_access_token, security
from modules.admin_auth.service import AdminAuthService, get_admin_service
from modules.admin_auth.schema import (
    AdminLoginRequest,
    AdminRegisterRequest,
    CreateAdminRequest,
    AdminValidateOtpRequest,
    AdminRefreshTokenRequest,
    AdminVerifyTokenRequest,
    AdminResponse,
    AdminTokenData,
    AdminAuthResponse,
    MessageResponse,
    UpdateAdminProfile,
)

router = APIRouter(
    prefix="/admin/auth",
    tags=["Admin Auth"],
)

admin_router = APIRouter(
    prefix="/admin",
    tags=["Admin"],
)

security_optional = HTTPBearer(auto_error=False)


@router.post("/create", response_model=ReturnType[AdminResponse], status_code=201)
@router.post("/admin", response_model=ReturnType[AdminResponse], status_code=201)
@admin_router.post("/create", response_model=ReturnType[AdminResponse], status_code=201)
@admin_router.post("", response_model=ReturnType[AdminResponse], status_code=201)
async def create_admin(
    payload: CreateAdminRequest,
    service: AdminAuthService = Depends(get_admin_service),
) -> ReturnType[AdminResponse]:
    """Create a new admin account directly (unprotected endpoint)."""
    try:
        return await service.create_admin(payload)
    except Exception as e:
        logger.error(f"Failed to create admin: {e}")
        raise BadRequestException(str(e))


@router.post("/register", response_model=ReturnType[AdminResponse], status_code=201)
async def register_admin(
    payload: AdminRegisterRequest,
    service: AdminAuthService = Depends(get_admin_service),
) -> ReturnType[AdminResponse]:
    """Register a new admin account and send OTP to their email."""
    try:
        return await service.register_admin(payload)
    except Exception as e:
        logger.error(f"Failed to register admin: {e}")
        raise BadRequestException(str(e))


@router.post("/login", response_model=ReturnType[MessageResponse], status_code=200)
async def login_admin(
    payload: AdminLoginRequest,
    service: AdminAuthService = Depends(get_admin_service),
) -> ReturnType[MessageResponse]:
    """Initiate passwordless login for an admin by sending OTP to email."""
    try:
        return await service.login_admin(payload)
    except Exception as e:
        logger.error(f"Failed to login admin: {e}")
        raise BadRequestException(str(e))


@router.post("/validate-otp", response_model=ReturnType[AdminAuthResponse], status_code=200)
async def validate_otp(
    payload: AdminValidateOtpRequest,
    service: AdminAuthService = Depends(get_admin_service),
) -> ReturnType[AdminAuthResponse]:
    """Validate OTP and issue JWT access & refresh tokens with admin claims."""
    try:
        return await service.validate_otp(payload)
    except Exception as e:
        logger.error(f"Failed to validate admin OTP: {e}")
        raise BadRequestException(str(e))


@router.post("/verify-token", response_model=ReturnType[AdminResponse], status_code=200)
async def verify_token_post(
    payload: AdminVerifyTokenRequest | None = None,
    credentials: HTTPAuthorizationCredentials | None = Depends(security_optional),
    service: AdminAuthService = Depends(get_admin_service),
) -> ReturnType[AdminResponse]:
    """Verify an admin access token provided either in request body or via Bearer authorization header."""
    try:
        raw_token: str | None = None
        if payload and payload.token:
            raw_token = payload.token.strip()
        elif credentials and credentials.credentials:
            raw_token = credentials.credentials.strip()

        if not raw_token:
            raise UnauthorizedException("Token must be provided in request body or Authorization header")

        return await service.verify_token(raw_token)
    except Exception as e:
        logger.error(f"Failed to verify admin token: {e}")
        raise UnauthorizedException(str(e))


@router.get("/verify-token", response_model=ReturnType[AdminResponse], status_code=200)
async def verify_token_get(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    service: AdminAuthService = Depends(get_admin_service),
) -> ReturnType[AdminResponse]:
    """Verify the admin access token provided in the Authorization header."""
    try:
        return await service.verify_token(credentials.credentials.strip())
    except Exception as e:
        logger.error(f"Failed to verify admin token: {e}")
        raise UnauthorizedException(str(e))


@router.post("/refresh-token", response_model=ReturnType[AdminTokenData], status_code=200)
async def refresh_token(
    payload: AdminRefreshTokenRequest,
    service: AdminAuthService = Depends(get_admin_service),
) -> ReturnType[AdminTokenData]:
    """Refresh admin access token using a valid refresh token."""
    try:
        return await service.refresh_token(payload)
    except Exception as e:
        logger.error(f"Failed to refresh admin token: {e}")
        raise BadRequestException(str(e))


@router.get("/me", response_model=ReturnType[AdminResponse], status_code=200)
@router.get("/details", response_model=ReturnType[AdminResponse], status_code=200)
async def get_current_admin(
    auth_data: dict = Depends(verify_access_token),
    service: AdminAuthService = Depends(get_admin_service),
) -> ReturnType[AdminResponse]:
    """Get profile and role details of the currently authenticated admin."""
    try:
        admin_id = auth_data.get("sub")
        return await service.get_current_admin_details(admin_id)
    except Exception as e:
        logger.error(f"Failed to fetch admin details: {e}")
        raise BadRequestException(str(e))


@router.patch("/me", response_model=ReturnType[AdminResponse], status_code=200)
async def update_current_admin(
    payload: UpdateAdminProfile,
    auth_data: dict = Depends(verify_access_token),
    service: AdminAuthService = Depends(get_admin_service),
) -> ReturnType[AdminResponse]:
    """Update profile details (name, profile_picture) of current admin."""
    try:
        admin_id = auth_data.get("sub")
        return await service.update_current_admin_details(admin_id, payload)
    except Exception as e:
        logger.error(f"Failed to update admin details: {e}")
        raise BadRequestException(str(e))
