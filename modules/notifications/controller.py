from uuid import UUID
from fastapi import APIRouter, Depends, Query

from common.classes.return_type import ReturnType
from common.services.auth import verify_access_token
from modules.notifications.schema import (
    CreateNotificationRequest,
    NotificationResponse,
)
from modules.notifications.service import (
    NotificationService,
    get_notification_service,
)

router = APIRouter(
    prefix="/notifications",
    tags=["Notifications"],
    responses={404: {"description": "Not found"}},
)


# ==========================================
# USER NOTIFICATION ENDPOINTS
# ==========================================


@router.get("", response_model=ReturnType[list[NotificationResponse]], status_code=200)
async def get_user_notifications(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    auth_data: dict = Depends(verify_access_token),
    service: NotificationService = Depends(get_notification_service),
) -> ReturnType[list[NotificationResponse]]:
    user_id = auth_data.get("sub")
    return await service.get_user_notifications(user_id=user_id, page=page, limit=limit)


@router.patch("/{notification_id}/read", response_model=ReturnType[NotificationResponse], status_code=200)
async def mark_user_notification_as_read(
    notification_id: UUID,
    auth_data: dict = Depends(verify_access_token),
    service: NotificationService = Depends(get_notification_service),
) -> ReturnType[NotificationResponse]:
    user_id = auth_data.get("sub")
    return await service.mark_user_notification_as_read(notification_id=notification_id, user_id=user_id)


# ==========================================
# ADMIN NOTIFICATION ENDPOINTS
# ==========================================


@router.get("/admin", response_model=ReturnType[list[NotificationResponse]], status_code=200)
async def get_admin_notifications(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    auth_data: dict = Depends(verify_access_token),
    service: NotificationService = Depends(get_notification_service),
) -> ReturnType[list[NotificationResponse]]:
    admin_id = auth_data.get("sub")
    return await service.get_admin_notifications(admin_id=admin_id, page=page, limit=limit)


@router.patch("/admin/{notification_id}/read", response_model=ReturnType[NotificationResponse], status_code=200)
async def mark_admin_notification_as_read(
    notification_id: UUID,
    auth_data: dict = Depends(verify_access_token),
    service: NotificationService = Depends(get_notification_service),
) -> ReturnType[NotificationResponse]:
    admin_id = auth_data.get("sub")
    return await service.mark_admin_notification_as_read(notification_id=notification_id, admin_id=admin_id)


# ==========================================
# TRIGGER NOTIFICATION ENDPOINT (API UTILITY)
# ==========================================


@router.post("/trigger", response_model=ReturnType[NotificationResponse], status_code=201)
async def trigger_notification(
    payload: CreateNotificationRequest,
    service: NotificationService = Depends(get_notification_service),
) -> ReturnType[NotificationResponse]:
    return await service.trigger_notification(
        title=payload.title,
        body=payload.body,
        user_id=payload.user_id,
        is_for_admin=payload.is_for_admin,
    )
