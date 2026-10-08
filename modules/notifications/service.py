from uuid import UUID
from typing import Optional
from sqlalchemy import select, func, not_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends

from common.database import get_db
from common.classes.return_type import ReturnType, Pagination
from common.exceptions.bad_request_exception import BadRequestException
from common.exceptions.internal_server_exception import InternalServerException
from common.exceptions.not_found_expection import NotFoundException
from common.logger import logger
from models.notification_model import Notification
from modules.notifications.schema import NotificationResponse


class NotificationService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def trigger_notification(
        self,
        title: str,
        body: str,
        user_id: Optional[UUID | str] = None,
        is_for_admin: bool = False,
    ) -> ReturnType[NotificationResponse]:
        """
        Can be invoked by other services to trigger notifications for users or admins.
        """
        try:
            logger.info(f"Triggering notification: '{title}' (is_for_admin={is_for_admin})")

            parsed_user_id: Optional[UUID] = None
            if user_id:
                parsed_user_id = UUID(str(user_id)) if not isinstance(user_id, UUID) else user_id

            notification = Notification(
                title=title,
                body=body,
                user_id=parsed_user_id,
                is_for_admin=is_for_admin,
                is_read=False,
                read_by=[],
            )

            self.db.add(notification)
            await self.db.commit()
            await self.db.refresh(notification)

            return ReturnType[NotificationResponse](
                success=True,
                message="Notification triggered successfully",
                data=NotificationResponse.model_validate(notification),
            )
        except Exception as e:
            logger.error(f"Error triggering notification: {str(e)}")
            await self.db.rollback()
            raise InternalServerException(str(e))

    async def get_user_notifications(
        self,
        user_id: UUID | str,
        page: int = 1,
        limit: int = 20,
    ) -> ReturnType[list[NotificationResponse]]:
        try:
            if page < 1:
                raise BadRequestException("Page must be greater than 0")
            if limit < 1:
                raise BadRequestException("Limit must be greater than 0")

            parsed_user_id = UUID(str(user_id)) if not isinstance(user_id, UUID) else user_id

            logger.info(f"Fetching notifications for user: {parsed_user_id} (page={page}, limit={limit})")

            count_stmt = (
                select(func.count())
                .select_from(Notification)
                .where(
                    Notification.user_id == parsed_user_id,
                    Notification.is_for_admin == False,
                    Notification.isDeleted == False,
                )
            )
            total_res = await self.db.execute(count_stmt)
            total = total_res.scalar_one()

            stmt = (
                select(Notification)
                .where(
                    Notification.user_id == parsed_user_id,
                    Notification.is_for_admin == False,
                    Notification.isDeleted == False,
                )
                .order_by(Notification.created_at.desc())
                .offset((page - 1) * limit)
                .limit(limit)
            )
            result = await self.db.execute(stmt)
            notifications = result.scalars().all()

            data = [NotificationResponse.model_validate(n) for n in notifications]

            return ReturnType[list[NotificationResponse]](
                success=True,
                message="User notifications fetched successfully",
                data=data,
                pagination=Pagination(
                    total=total,
                    page=page,
                    per_page=limit,
                ),
            )
        except BadRequestException:
            raise
        except Exception as e:
            logger.error(f"Error fetching user notifications: {str(e)}")
            raise InternalServerException(str(e))

    async def mark_user_notification_as_read(
        self,
        notification_id: UUID | str,
        user_id: UUID | str,
    ) -> ReturnType[NotificationResponse]:
        try:
            parsed_notification_id = (
                UUID(str(notification_id)) if not isinstance(notification_id, UUID) else notification_id
            )
            parsed_user_id = UUID(str(user_id)) if not isinstance(user_id, UUID) else user_id

            logger.info(f"Marking notification {parsed_notification_id} as read for user {parsed_user_id}")

            stmt = select(Notification).where(
                Notification.id == parsed_notification_id,
                Notification.user_id == parsed_user_id,
                Notification.isDeleted == False,
            )
            result = await self.db.execute(stmt)
            notification = result.scalar_one_or_none()

            if not notification:
                raise NotFoundException("Notification not found")

            notification.is_read = True
            await self.db.commit()
            await self.db.refresh(notification)

            return ReturnType[NotificationResponse](
                success=True,
                message="Notification marked as read",
                data=NotificationResponse.model_validate(notification),
            )
        except (NotFoundException, BadRequestException):
            raise
        except Exception as e:
            logger.error(f"Error marking notification as read: {str(e)}")
            await self.db.rollback()
            raise InternalServerException(str(e))

    async def get_admin_notifications(
        self,
        admin_id: UUID | str,
        page: int = 1,
        limit: int = 20,
    ) -> ReturnType[list[NotificationResponse]]:
        try:
            if page < 1:
                raise BadRequestException("Page must be greater than 0")
            if limit < 1:
                raise BadRequestException("Limit must be greater than 0")

            admin_id_str = str(admin_id)
            logger.info(f"Fetching unread admin notifications for admin: {admin_id_str} (page={page}, limit={limit})")

            # Condition: Admin notifications not read by this admin
            unread_condition = or_(
                Notification.read_by.is_(None),
                not_(Notification.read_by.any(admin_id_str)),
            )

            count_stmt = (
                select(func.count())
                .select_from(Notification)
                .where(
                    Notification.is_for_admin == True,
                    Notification.isDeleted == False,
                    unread_condition,
                )
            )
            total_res = await self.db.execute(count_stmt)
            total = total_res.scalar_one()

            stmt = (
                select(Notification)
                .where(
                    Notification.is_for_admin == True,
                    Notification.isDeleted == False,
                    unread_condition,
                )
                .order_by(Notification.created_at.desc())
                .offset((page - 1) * limit)
                .limit(limit)
            )
            result = await self.db.execute(stmt)
            notifications = result.scalars().all()

            data = [NotificationResponse.model_validate(n) for n in notifications]

            return ReturnType[list[NotificationResponse]](
                success=True,
                message="Admin notifications fetched successfully",
                data=data,
                pagination=Pagination(
                    total=total,
                    page=page,
                    per_page=limit,
                ),
            )
        except BadRequestException:
            raise
        except Exception as e:
            logger.error(f"Error fetching admin notifications: {str(e)}")
            raise InternalServerException(str(e))

    async def mark_admin_notification_as_read(
        self,
        notification_id: UUID | str,
        admin_id: UUID | str,
    ) -> ReturnType[NotificationResponse]:
        try:
            parsed_notification_id = (
                UUID(str(notification_id)) if not isinstance(notification_id, UUID) else notification_id
            )
            admin_id_str = str(admin_id)

            logger.info(f"Marking admin notification {parsed_notification_id} as read for admin {admin_id_str}")

            stmt = select(Notification).where(
                Notification.id == parsed_notification_id,
                Notification.is_for_admin == True,
                Notification.isDeleted == False,
            )
            result = await self.db.execute(stmt)
            notification = result.scalar_one_or_none()

            if not notification:
                raise NotFoundException("Admin notification not found")

            read_by_list = list(notification.read_by or [])
            if admin_id_str not in read_by_list:
                read_by_list.append(admin_id_str)
                notification.read_by = read_by_list

            notification.is_read = True

            await self.db.commit()
            await self.db.refresh(notification)

            return ReturnType[NotificationResponse](
                success=True,
                message="Admin notification marked as read",
                data=NotificationResponse.model_validate(notification),
            )
        except (NotFoundException, BadRequestException):
            raise
        except Exception as e:
            logger.error(f"Error marking admin notification as read: {str(e)}")
            await self.db.rollback()
            raise InternalServerException(str(e))


def get_notification_service(db: AsyncSession = Depends(get_db)) -> NotificationService:
    return NotificationService(db)
