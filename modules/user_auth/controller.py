from fastapi import APIRouter, Depends
from common.classes.return_type import ReturnType
from common.exceptions.bad_request_exception import BadRequestException
from common.logger import logger
from common.services.auth import verify_access_token
from modules.user_auth.service import get_user_service, UserService
from modules.user_auth.schema import (
    CreateUser,
    UpdateUser,
    LoginRequest,
    ValidateOtpRequest,
    GoogleAuthRequest,
    RefreshTokenRequest,
    UserResponse,
    TokenData,
    AuthTokenResponse,
    MessageResponse,
)

router = APIRouter(
    prefix="/auth",
    tags=["Auth"],
)


@router.post("/register", response_model=ReturnType[UserResponse], status_code=201)
async def register_user(
    payload: CreateUser,
    service: UserService = Depends(get_user_service),
) -> ReturnType[UserResponse]:
    try:
        return await service.register_user(payload)
    except Exception as e:
        logger.error("Failed to register user: " + str(e))
        raise BadRequestException(str(e))


@router.post("/login", response_model=ReturnType[MessageResponse], status_code=200)
async def login_user(
    payload: LoginRequest,
    service: UserService = Depends(get_user_service),
) -> ReturnType[MessageResponse]:
    try:
        return await service.login_user(payload)
    except Exception as e:
        logger.error("Failed to login user: " + str(e))
        raise BadRequestException(str(e))


@router.post("/validate-otp", response_model=ReturnType[AuthTokenResponse], status_code=200)
async def validate_otp(
    payload: ValidateOtpRequest,
    service: UserService = Depends(get_user_service),
) -> ReturnType[AuthTokenResponse]:
    try:
        return await service.validate_otp(payload)
    except Exception as e:
        logger.error("Failed to validate OTP: " + str(e))
        raise BadRequestException(str(e))


@router.post("/google", response_model=ReturnType[AuthTokenResponse], status_code=200)
async def google_auth(
    payload: GoogleAuthRequest,
    service: UserService = Depends(get_user_service),
) -> ReturnType[AuthTokenResponse]:
    try:
        return await service.google_auth(payload)
    except Exception as e:
        logger.error("Failed Google auth: " + str(e))
        raise BadRequestException(str(e))


@router.post("/refresh-token", response_model=ReturnType[TokenData], status_code=200)
async def refresh_token(
    payload: RefreshTokenRequest,
    service: UserService = Depends(get_user_service),
) -> ReturnType[TokenData]:
    try:
        return await service.refresh_token(payload)
    except Exception as e:
        logger.error("Failed to refresh token: " + str(e))
        raise BadRequestException(str(e))


@router.get("/me", response_model=ReturnType[UserResponse], status_code=200)
async def get_current_user(
    auth_data: dict = Depends(verify_access_token),
    service: UserService = Depends(get_user_service),
) -> ReturnType[UserResponse]:
    try:
        user_id = auth_data.get("sub")
        return await service.get_current_user_details(user_id)
    except Exception as e:
        logger.error("Failed to fetch current user details: " + str(e))
        raise BadRequestException(str(e))


@router.patch("/me", response_model=ReturnType[UserResponse], status_code=200)
async def update_current_user(
    payload: UpdateUser,
    auth_data: dict = Depends(verify_access_token),
    service: UserService = Depends(get_user_service),
) -> ReturnType[UserResponse]:
    try:
        user_id = auth_data.get("sub")
        return await service.update_user_details(user_id, payload)
    except Exception as e:
        logger.error("Failed to update user details: " + str(e))
        raise BadRequestException(str(e))
