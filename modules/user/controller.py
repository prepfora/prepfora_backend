from uuid import UUID
from fastapi import APIRouter, Depends, Query
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
from modules.user.schema import UserDetailResponse, UserListItemResponse
from modules.user.service import (
    UserManagementService,
    get_user_management_service,
)


async def require_admin_access(
    auth_data: dict = Depends(verify_access_token),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Ensures only authorized admins can access admin user management endpoints.
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
    prefix="/users",
    tags=["Users"],
    responses={403: {"description": "Forbidden"}},
)

admin_users_router = APIRouter(
    prefix="/admin/users",
    tags=["Admin Users"],
    responses={403: {"description": "Forbidden"}},
)


# 1. Get all users in the platform (with name / email search and pagination)
@router.get("", response_model=ReturnType[list[UserListItemResponse]], status_code=200)
@router.get("/all", response_model=ReturnType[list[UserListItemResponse]], status_code=200)
@admin_users_router.get("", response_model=ReturnType[list[UserListItemResponse]], status_code=200)
@admin_users_router.get("/all", response_model=ReturnType[list[UserListItemResponse]], status_code=200)
async def get_all_users(
    search: str | None = Query(
        None,
        description="Search users by first name, last name, full name, or email",
    ),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    _admin: dict = Depends(require_admin_access),
    service: UserManagementService = Depends(get_user_management_service),
) -> ReturnType[list[UserListItemResponse]]:
    """
    Admin-only endpoint to get all platform users with optional search and pagination.
    """
    try:
        return await service.get_all_users(page=page, limit=limit, search=search)
    except APIException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch users: {e}")
        raise BadRequestException(str(e))


# 2. Get user by ID (with total exams, mock, practice, and badges)
@router.get("/{id}", response_model=ReturnType[UserDetailResponse], status_code=200)
@admin_users_router.get("/{id}", response_model=ReturnType[UserDetailResponse], status_code=200)
async def get_user_by_id(
    id: UUID,
    _admin: dict = Depends(require_admin_access),
    service: UserManagementService = Depends(get_user_management_service),
) -> ReturnType[UserDetailResponse]:
    """
    Admin-only endpoint to get user details by user ID, including:
    - total exams
    - total mock exams
    - total practice exams
    - total badges
    """
    try:
        return await service.get_user_by_id(id)
    except APIException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch user by id {id}: {e}")
        raise BadRequestException(str(e))
