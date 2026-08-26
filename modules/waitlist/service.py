
from common.services.event_emitters import Send_Email_Payload
from common.services.emaill_service import ResendPayload
from common.classes.return_type import Pagination
from sqlalchemy import func
from fastapi import param_functions
from common.logger import logger
from common.exceptions.bad_request_exception import BadRequestException
from modules.waitlist.schema import CreateWaitListEntry
from sqlalchemy import select
from modules.waitlist.schema import WaitListReturnType
from common.classes.return_type import ReturnType
from common.database import get_db
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from models.waitlist_model import Waitlist
from common.exceptions.internal_server_exception import InternalServerException
from common.services.emaill_service import send_email
from common.services.event_emitters import ee
# from modules.waitlist.schema import SendWaitlistEmailPayload


def _build_welcome_email_html(first_name: str | None = None) -> str:
    greeting_name = first_name.strip().capitalize() if first_name and first_name.strip() else "there"
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Welcome to Prefora</title>
</head>
<body style="margin: 0; padding: 0; background-color: #f4f6f9; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; color: #1e293b;">
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background-color: #f4f6f9; padding: 40px 16px;">
        <tr>
            <td align="center">
                <table role="presentation" width="100%" style="max-width: 600px; background-color: #ffffff; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03);">
                    <!-- Header -->
                    <tr>
                        <td style="background-color: #0f172a; padding: 32px 40px; text-align: center;">
                            <h1 style="margin: 0; color: #ffffff; font-size: 26px; font-weight: 700; letter-spacing: -0.5px;">Prefora</h1>
                        </td>
                    </tr>
                    
                    <!-- Content Body -->
                    <tr>
                        <td style="padding: 40px;">
                            <h2 style="margin: 0 0 16px 0; color: #0f172a; font-size: 22px; font-weight: 600;">
                                You're on the waitlist! 🎉
                            </h2>
                            <p style="margin: 0 0 16px 0; font-size: 16px; line-height: 1.6; color: #475569;">
                                Hi {greeting_name},
                            </p>
                            <p style="margin: 0 0 24px 0; font-size: 16px; line-height: 1.6; color: #475569;">
                                Thank you for joining the <strong>Prefora</strong> waitlist! We are building something special, and we are thrilled to have you onboard from the ground level.
                            </p>
                            
                            <!-- Highlight Box -->
                            <div style="background-color: #f8fafc; border-left: 4px solid #2563eb; border-radius: 6px; padding: 20px; margin-bottom: 28px;">
                                <h3 style="margin: 0 0 12px 0; font-size: 16px; font-weight: 600; color: #1e293b;">
                                    What to expect next:
                                </h3>
                                <ul style="margin: 0; padding-left: 20px; font-size: 15px; line-height: 1.6; color: #475569;">
                                    <li style="margin-bottom: 8px;"><strong>Priority Access:</strong> You'll be among the first to get access when we launch.</li>
                                    <li style="margin-bottom: 8px;"><strong>Exclusive Updates:</strong> We'll share behind-the-scenes progress and sneak peeks.</li>
                                    <li><strong>Direct Input:</strong> You will get opportunities to share your feedback to help shape Prefora.</li>
                                </ul>
                            </div>
                            
                            <p style="margin: 0 0 24px 0; font-size: 16px; line-height: 1.6; color: #475569;">
                                If you have any questions or ideas in the meantime, feel free to reply directly to this email—we'd love to hear from you.
                            </p>
                            
                            <p style="margin: 0; font-size: 16px; line-height: 1.6; color: #475569;">
                                Warmly,<br>
                                <strong>The Prefora Team</strong>
                            </p>
                        </td>
                    </tr>
                    
                    <!-- Footer -->
                    <tr>
                        <td style="background-color: #f8fafc; padding: 24px 40px; text-align: center; border-top: 1px solid #e2e8f0;">
                            <p style="margin: 0; font-size: 13px; color: #94a3b8; line-height: 1.5;">
                                &copy; 2026 Prefora. All rights reserved.
                            </p>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>
</body>
</html>"""


class WaitlistService:
    db: AsyncSession

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_wait_list_entry(self, payload: CreateWaitListEntry) -> ReturnType[WaitListReturnType]:
        try:
            stmt = select(Waitlist).where(Waitlist.email == payload.email.lower())
            result = await self.db.execute(stmt)
            check = result.scalars().first()
            logger.error("CHECK VALUE")
            logger.error(str(check))
            if  check is not None:
                raise BadRequestException("User already exists in waitlist")
            entry = Waitlist(
                email=payload.email.lower(),
                first_name=payload.first_name,
                last_name=payload.last_name,
                phone_number=payload.phone_number,
            )
            self.db.add(entry)
            await self.db.commit()
            await self.db.refresh(entry)
            
            send_email(
                payload=ResendPayload(
                    to=entry.email,
                    subject="Welcome to Prefora! 🎉",
                    html=_build_welcome_email_html(entry.first_name),
                    template=None
                )
            )
            return ReturnType[WaitListReturnType](
                success=True,
                message="Waitlist entry created successfully",
                data=WaitListReturnType(
                    email=entry.email,
                    first_name=entry.first_name,
                    last_name=entry.last_name,
                    phone_number=entry.phone_number,
                    id=entry.id,
                    created_at=entry.created_at,
                    updated_at=entry.updated_at,
                    isDeleted=entry.isDeleted,
                    deleted_at=entry.deleted_at
                )
            )
        except Exception as e:
            logger.error(str(e))
            raise InternalServerException(str(e))

    async def get_waitlist_entries(self, page: int = 1, limit: int = 20) -> ReturnType[list[WaitListReturnType]]:
        try:
            if page < 1:
                logger.error("Page must be greater then 0")
                raise BadRequestException("Page must be greater than 0")
            if limit < 1:
                logger.error("Limit must be greater than 0")
                raise BadRequestException("Limit must be greater than 0")
            logger.info("Fetching waitlist entries")
            count_stmt = select(func.count()).select_from(Waitlist).where(Waitlist.isDeleted == False)
            total_result = await self.db.execute(count_stmt)
            total = total_result.scalar_one()
            stmt = (
                select(Waitlist)
                .where(Waitlist.isDeleted == False)
                .offset((page - 1) * limit)
                .limit(limit)
            )
            result = await self.db.execute(stmt)
            entries = list(result.scalars().all())
            logger.info("Waitlist entries fetched successfully")
            return ReturnType[list[WaitListReturnType]](
                success=True,
                message="Waitlist entries fetched successfully",
                data=entries,
                pagination=Pagination(
                    total=total,
                    page=page,
                    per_page=limit,
                )
            )
        except Exception as e:
            logger.error("Error fetching waitlist entries: " + str(e))
            raise InternalServerException(str(e))
    
    async def send_email_to_users(self, emails: list[str], message: str, subject: str) -> ReturnType[str]:
        if (len(emails) < 1):
            logger.info('NO EMAIL TO SEND TO')
            raise BadRequestException("No email to send to")
        payload = Send_Email_Payload(
            emails=emails,
            message=message,
            subject=subject
        )
        ee.emit("send_emails", payload)

    async def get_total_waitlist_entries(self) -> ReturnType[int]:
        try:
            logger.info("Fetching total waitlist entries")
            count_stmt = select(func.count()).select_from(Waitlist).where(Waitlist.isDeleted == False)
            total_result = await self.db.execute(count_stmt)
            total = total_result.scalar_one()
            logger.info("Total waitlist entries fetched successfully")
            return ReturnType[int](
                success=True,
                message="Total waitlist entries fetched successfully",
                data=total
            )
        except Exception as e:
            logger.error("Error fetching total waitlist entries: " + str(e))
            raise InternalServerException(str(e))

    

    
            
        

### WAITLIST DEPENDENCY
def get_waitlist_service(
    db: AsyncSession = Depends(get_db),
) -> WaitlistService:
    return WaitlistService(db)


#### waitlist service

    
            
        

### WAITLIST DEPENDENCY
def get_waitlist_service(
    db: AsyncSession = Depends(get_db),
) -> WaitlistService:
    return WaitlistService(db)