import uuid
from fastapi import APIRouter, Depends, Path, Query

from common.classes.return_type import ReturnType
from common.exceptions.api_exception import APIException
from common.exceptions.bad_request_exception import BadRequestException
from common.logger import logger
from common.services.auth import verify_access_token
from modules.badges.schema import (
    BadgeResponse,
    CreateBadge,
    UpdateBadge,
    UserBadgeDetailResponse,
)
from modules.badges.service import BadgeService, get_badge_service


router = APIRouter(
    prefix="/badges",
    tags=["Badges"],
)


@router.get("", response_model=ReturnType[list[BadgeResponse]], status_code=200)
async def get_all_badges(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    active_only: bool = Query(True, description="Return only active badges"),
    service: BadgeService = Depends(get_badge_service),
) -> ReturnType[list[BadgeResponse]]:
    try:
        return await service.get_all_badges(page=page, limit=limit, active_only=active_only)
    except APIException:
        raise
    except Exception as e:
        logger.error("Failed to fetch badges: " + str(e))
        raise BadRequestException(str(e))


@router.post("/seed", response_model=ReturnType[list[BadgeResponse]], status_code=200)
async def seed_default_badges(
    service: BadgeService = Depends(get_badge_service),
) -> ReturnType[list[BadgeResponse]]:
    try:
        badges = await service.seed_default_badges()
        return ReturnType[list[BadgeResponse]](
            success=True,
            message="Default badges seeded successfully",
            data=[BadgeResponse.model_validate(b) for b in badges],
        )
    except APIException:
        raise
    except Exception as e:
        logger.error("Failed to seed badges: " + str(e))
        raise BadRequestException(str(e))


@router.get("/me", response_model=ReturnType[list[UserBadgeDetailResponse]], status_code=200)
async def get_my_badges(
    auth_data: dict = Depends(verify_access_token),
    service: BadgeService = Depends(get_badge_service),
) -> ReturnType[list[UserBadgeDetailResponse]]:
    try:
        user_id = uuid.UUID(str(auth_data.get("sub")))
        return await service.get_user_badges(user_id)
    except APIException:
        raise
    except Exception as e:
        logger.error("Failed to fetch current user badges: " + str(e))
        raise BadRequestException(str(e))


@router.get("/user/{user_id}", response_model=ReturnType[list[UserBadgeDetailResponse]], status_code=200)
async def get_user_badges(
    user_id: uuid.UUID = Path(..., description="User ID"),
    service: BadgeService = Depends(get_badge_service),
) -> ReturnType[list[UserBadgeDetailResponse]]:
    try:
        return await service.get_user_badges(user_id)
    except APIException:
        raise
    except Exception as e:
        logger.error("Failed to fetch user badges: " + str(e))
        raise BadRequestException(str(e))


@router.post("/evaluate/{user_id}", response_model=ReturnType[list[BadgeResponse]], status_code=200)
async def evaluate_user_badges(
    user_id: uuid.UUID = Path(..., description="User ID"),
    service: BadgeService = Depends(get_badge_service),
) -> ReturnType[list[BadgeResponse]]:
    try:
        return await service.evaluate_all_badges_for_user(user_id)
    except APIException:
        raise
    except Exception as e:
        logger.error("Failed to evaluate user badges: " + str(e))
        raise BadRequestException(str(e))


@router.get("/{id}", response_model=ReturnType[BadgeResponse], status_code=200)
async def get_badge_by_id(
    id: uuid.UUID = Path(..., description="Badge ID"),
    service: BadgeService = Depends(get_badge_service),
) -> ReturnType[BadgeResponse]:
    try:
        return await service.get_badge_by_id(id)
    except APIException:
        raise
    except Exception as e:
        logger.error("Failed to fetch badge: " + str(e))
        raise BadRequestException(str(e))


@router.post("", response_model=ReturnType[BadgeResponse], status_code=201)
async def create_badge(
    payload: CreateBadge,
    service: BadgeService = Depends(get_badge_service),
) -> ReturnType[BadgeResponse]:
    try:
        return await service.create_badge(payload)
    except APIException:
        raise
    except Exception as e:
        logger.error("Failed to create badge: " + str(e))
        raise BadRequestException(str(e))


@router.put("/{id}", response_model=ReturnType[BadgeResponse], status_code=200)
async def update_badge(
    payload: UpdateBadge,
    id: uuid.UUID = Path(..., description="Badge ID"),
    service: BadgeService = Depends(get_badge_service),
) -> ReturnType[BadgeResponse]:
    try:
        return await service.update_badge(id, payload)
    except APIException:
        raise
    except Exception as e:
        logger.error("Failed to update badge: " + str(e))
        raise BadRequestException(str(e))


@router.delete("/{id}", response_model=ReturnType[BadgeResponse], status_code=200)
async def delete_badge(
    id: uuid.UUID = Path(..., description="Badge ID"),
    service: BadgeService = Depends(get_badge_service),
) -> ReturnType[BadgeResponse]:
    try:
        return await service.delete_badge(id)
    except APIException:
        raise
    except Exception as e:
        logger.error("Failed to delete badge: " + str(e))
        raise BadRequestException(str(e))
