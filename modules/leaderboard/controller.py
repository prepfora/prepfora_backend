import uuid
from fastapi import APIRouter, Depends, Path, Query

from common.classes.return_type import ReturnType
from common.exceptions.api_exception import APIException
from common.exceptions.bad_request_exception import BadRequestException
from common.logger import logger
from common.services.auth import verify_access_token
from models.examination_model import ExaminationType, Type
from modules.leaderboard.schema import LeaderboardEntry, LeaderboardResponse
from modules.leaderboard.service import LeaderboardService, get_leaderboard_service


router = APIRouter(
    prefix="/leaderboard",
    tags=["Leaderboard"],
)


@router.get("", response_model=ReturnType[LeaderboardResponse], status_code=200)
async def get_leaderboard(
    exam_type: ExaminationType | str = Query(
        ...,
        description="Exam type to rank by (e.g. jamb, utme, waec, neco, post-utme)",
    ),
    type: Type | str | None = Query(
        None,
        description="Optional examination mode filter (mock or practice)",
    ),
    user_id: uuid.UUID | None = Query(
        None,
        description="Optional user ID to include their current rank in the response",
    ),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    service: LeaderboardService = Depends(get_leaderboard_service),
) -> ReturnType[LeaderboardResponse]:
    try:
        exam_type_str = exam_type.value if hasattr(exam_type, "value") else str(exam_type)
        mode_str = type.value if hasattr(type, "value") else (str(type) if type else None)
        return await service.get_leaderboard(
            exam_type=exam_type_str,
            exam_mode=mode_str,
            page=page,
            limit=limit,
            current_user_id=user_id,
        )
    except APIException:
        raise
    except Exception as e:
        logger.error("Failed to fetch leaderboard: " + str(e))
        raise BadRequestException(str(e))


@router.get("/me", response_model=ReturnType[LeaderboardEntry | None], status_code=200)
async def get_my_leaderboard_rank(
    exam_type: ExaminationType | str = Query(
        ...,
        description="Exam type to check rank for (e.g. jamb, utme, waec, neco, post-utme)",
    ),
    type: Type | str | None = Query(
        None,
        description="Optional examination mode filter (mock or practice)",
    ),
    auth_data: dict = Depends(verify_access_token),
    service: LeaderboardService = Depends(get_leaderboard_service),
) -> ReturnType[LeaderboardEntry | None]:
    try:
        user_id = uuid.UUID(str(auth_data.get("sub")))
        exam_type_str = exam_type.value if hasattr(exam_type, "value") else str(exam_type)
        mode_str = type.value if hasattr(type, "value") else (str(type) if type else None)
        return await service.get_user_rank(
            user_id=user_id,
            exam_type=exam_type_str,
            exam_mode=mode_str,
        )
    except APIException:
        raise
    except Exception as e:
        logger.error("Failed to fetch current user leaderboard rank: " + str(e))
        raise BadRequestException(str(e))


@router.get("/{exam_type}", response_model=ReturnType[LeaderboardResponse], status_code=200)
async def get_leaderboard_by_exam_type(
    exam_type: ExaminationType | str = Path(
        ...,
        description="Exam type to rank by (e.g. jamb, utme, waec, neco, post-utme)",
    ),
    type: Type | str | None = Query(
        None,
        description="Optional examination mode filter (mock or practice)",
    ),
    user_id: uuid.UUID | None = Query(
        None,
        description="Optional user ID to include their current rank in the response",
    ),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    service: LeaderboardService = Depends(get_leaderboard_service),
) -> ReturnType[LeaderboardResponse]:
    try:
        exam_type_str = exam_type.value if hasattr(exam_type, "value") else str(exam_type)
        mode_str = type.value if hasattr(type, "value") else (str(type) if type else None)
        return await service.get_leaderboard(
            exam_type=exam_type_str,
            exam_mode=mode_str,
            page=page,
            limit=limit,
            current_user_id=user_id,
        )
    except APIException:
        raise
    except Exception as e:
        logger.error("Failed to fetch leaderboard by exam_type: " + str(e))
        raise BadRequestException(str(e))
