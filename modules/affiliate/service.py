import os
import random
import string
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from common.classes.return_type import ReturnType
from common.database import get_db
from common.exceptions.bad_request_exception import BadRequestException
from common.exceptions.forbidden_exception import ForbiddenException
from common.exceptions.internal_server_exception import InternalServerException
from common.exceptions.not_found_expection import NotFoundException
from common.exceptions.unauthorized_exception import UnauthorizedException
from common.logger import logger
from common.services.auth import create_access_token, decode_token
from common.services.emaill_service import ResendPayload, send_email
from models.affiliate_model import Affiliate
from models.invite_model import Invite
from models.otp_model import Otp
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


class AffiliateService:
    db: AsyncSession

    def __init__(self, db: AsyncSession):
        self.db = db

    async def _generate_unique_invite_code(self) -> str:
        """Generates a unique 6-digit code for an invite."""
        for _ in range(20):
            code = f"{random.randint(100000, 999999)}"
            stmt = select(Invite).where(
                Invite.code == code,
                Invite.isActive == True,
                Invite.isDeleted == False,
            )
            result = await self.db.execute(stmt)
            if result.scalars().first() is None:
                return code
        raise InternalServerException("Failed to generate a unique invite code. Please try again.")

    async def _generate_unique_affiliate_code(self, base_name: str | None = None) -> str:
        """Generates a unique referral code for the affiliate."""
        prefix = "PREF"
        if base_name:
            clean_name = "".join(filter(str.isalnum, base_name)).upper()
            if len(clean_name) >= 3:
                prefix = clean_name[:4]

        for _ in range(20):
            suffix = "".join(random.choices(string.ascii_uppercase + string.digits, k=4))
            candidate = f"{prefix}-{suffix}"
            stmt = select(Affiliate).where(
                Affiliate.code == candidate,
                Affiliate.isDeleted == False,
            )
            result = await self.db.execute(stmt)
            if result.scalars().first() is None:
                return candidate

        # Fallback to pure alphanumeric code
        for _ in range(20):
            candidate = "".join(random.choices(string.ascii_uppercase + string.digits, k=8))
            stmt = select(Affiliate).where(
                Affiliate.code == candidate,
                Affiliate.isDeleted == False,
            )
            result = await self.db.execute(stmt)
            if result.scalars().first() is None:
                return candidate

        raise InternalServerException("Failed to generate a unique affiliate referral code.")

    def _is_date_expired(self, end_date: datetime | str) -> bool:
        """Checks if a given datetime or ISO string has expired relative to current UTC time."""
        if isinstance(end_date, str):
            try:
                dt = datetime.fromisoformat(end_date)
            except Exception:
                return True
        else:
            dt = end_date

        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)

        return datetime.now(timezone.utc) > dt

    async def send_invite(self, payload: SendInviteRequest) -> ReturnType[InviteResponse]:
        """
        Sends an invite to a prospective affiliate:
        1. Checks that the affiliate is not already registered.
        2. Generates a unique 6-digit invite code expiring in 24 hours.
        3. Deactivates any previous active invites for this email.
        4. Saves the new Invite record.
        5. Sends an invitation email with a joining link and the 6-digit code.
        """
        try:
            email = payload.email.strip().lower()

            # 1. Verify affiliate does not already exist
            affiliate_stmt = select(Affiliate).where(
                Affiliate.email == email,
                Affiliate.isDeleted == False,
            )
            affiliate_res = await self.db.execute(affiliate_stmt)
            if affiliate_res.scalars().first() is not None:
                raise BadRequestException("An affiliate account with this email already exists")

            # 2. Generate unique 6-digit code
            code = await self._generate_unique_invite_code()

            # 3. Expiration in 24 hours
            end_date = datetime.now(timezone.utc) + timedelta(hours=24)

            # 4. Deactivate prior active invites for this email
            prev_stmt = select(Invite).where(
                Invite.email == email,
                Invite.isActive == True,
                Invite.isDeleted == False,
            )
            prev_res = await self.db.execute(prev_stmt)
            for prev_invite in prev_res.scalars().all():
                prev_invite.isActive = False

            # 5. Create new Invite record
            invite = Invite(
                email=email,
                code=code,
                isActive=True,
                endDate=end_date,
            )
            self.db.add(invite)
            await self.db.commit()
            await self.db.refresh(invite)

            # 6. Form join link
            base_url = (
                payload.invite_url.strip()
                if payload.invite_url
                else os.getenv("AFFILIATE_PORTAL_URL", "https://prepfora.com/affiliate/register")
            )
            separator = "&" if "?" in base_url else "?"
            join_link = f"{base_url}{separator}code={code}&email={email}"

            # 7. Send invitation email
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
              <meta charset="utf-8">
              <style>
                body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f8fafc; margin: 0; padding: 24px; color: #1e293b; }}
                .container {{ max-width: 580px; margin: 0 auto; background: #ffffff; border-radius: 12px; padding: 36px; border: 1px solid #e2e8f0; }}
                .header {{ text-align: center; margin-bottom: 24px; }}
                .badge {{ display: inline-block; background: #dbeafe; color: #1d4ed8; font-weight: 600; font-size: 13px; padding: 4px 12px; border-radius: 9999px; text-transform: uppercase; letter-spacing: 0.5px; }}
                .code-box {{ background-color: #eff6ff; border: 2px dashed #3b82f6; border-radius: 10px; padding: 20px; text-align: center; margin: 28px 0; }}
                .code {{ font-size: 36px; font-weight: 800; letter-spacing: 8px; color: #1e40af; font-family: monospace; }}
                .expiry {{ margin-top: 8px; font-size: 14px; color: #dc2626; font-weight: 600; }}
                .btn-container {{ text-align: center; margin: 32px 0; }}
                .button {{ display: inline-block; background-color: #2563eb; color: #ffffff !important; padding: 14px 32px; font-size: 16px; font-weight: 600; text-decoration: none; border-radius: 8px; }}
                .footer {{ margin-top: 36px; font-size: 12px; color: #94a3b8; text-align: center; border-top: 1px solid #f1f5f9; padding-top: 20px; }}
              </style>
            </head>
            <body>
              <div class="container">
                <div class="header">
                  <span class="badge">Affiliate Invitation</span>
                  <h1 style="color: #0f172a; margin: 12px 0 0; font-size: 24px;">Join Prefora Affiliate Program</h1>
                </div>
                <p>Hello,</p>
                <p>You have been personally invited to become an official affiliate partner with <strong>Prefora</strong>. Partnering with us allows you to earn rewards while helping students achieve academic success.</p>
                <p>Here is your unique 6-digit invitation code:</p>
                <div class="code-box">
                  <div class="code">{code}</div>
                  <div class="expiry">Expires in 24 hours</div>
                </div>
                <div class="btn-container">
                  <a href="{join_link}" class="button" target="_blank">Join Prefora Platform</a>
                </div>
                <p style="font-size: 13px; color: #64748b; line-height: 1.5;">Or paste this link into your browser:<br><a href="{join_link}" style="color: #2563eb; word-break: break-all;">{join_link}</a></p>
                <div class="footer">
                  <p>&copy; Prefora. All rights reserved.<br>If you did not request this invitation, please disregard this email.</p>
                </div>
              </div>
            </body>
            </html>
            """
            try:
                send_email(
                    ResendPayload(
                        to=email,
                        subject="You're Invited to Join Prefora as an Affiliate",
                        html=html_content,
                    )
                )
            except Exception as mail_err:
                logger.error(f"Failed to send affiliate invite email: {mail_err}")

            response_data = InviteResponse(
                id=invite.id,
                code=invite.code,
                email=invite.email,
                isActive=invite.isActive,
                endDate=invite.endDate,
                invite_link=join_link,
                created_at=invite.created_at,
                updated_at=invite.updated_at,
            )

            return ReturnType[InviteResponse](
                success=True,
                message="Invite sent successfully to affiliate",
                data=response_data,
            )
        except (BadRequestException, NotFoundException, UnauthorizedException, ForbiddenException):
            raise
        except Exception as e:
            logger.error(f"Error in send_invite: {e}")
            raise InternalServerException(str(e))

    async def register_affiliate(
        self,
        payload: AffiliateRegisterRequest,
    ) -> ReturnType[AffiliateAuthResponse]:
        """
        Registers an affiliate account after strictly verifying the 6-digit invite code:
        1. Checks that an affiliate with this email doesn't already exist.
        2. Verifies the invite code exists, is active, matches email, and has not expired.
        3. Generates the affiliate referral code.
        4. Creates the Affiliate account.
        5. Marks the invite as not active (isActive = False).
        6. Issues JWT access & refresh tokens.
        """
        try:
            email = payload.email.strip().lower()
            invite_code = payload.invite_code.strip()

            # 1. Check if affiliate already exists
            existing_stmt = select(Affiliate).where(
                Affiliate.email == email,
                Affiliate.isDeleted == False,
            )
            existing_res = await self.db.execute(existing_stmt)
            if existing_res.scalars().first() is not None:
                raise BadRequestException("An affiliate account with this email already exists")

            # 2. Look up the invite by code
            invite_stmt = (
                select(Invite)
                .where(
                    Invite.code == invite_code,
                    Invite.isDeleted == False,
                )
                .order_by(Invite.created_at.desc())
            )
            invite_res = await self.db.execute(invite_stmt)
            invite = invite_res.scalars().first()

            if invite is None:
                raise BadRequestException("Invalid invite code")

            # 3. Verify invite is active
            if not invite.isActive:
                raise BadRequestException("Invite code is inactive or has already been used")

            # 4. Verify invite belongs to this email
            if invite.email.strip().lower() != email:
                raise BadRequestException("Invite code does not match the provided email address")

            # 5. Verify invite has not expired
            if self._is_date_expired(invite.endDate):
                invite.isActive = False
                await self.db.commit()
                raise BadRequestException("Invite code has expired. Please request a new invitation.")

            # 6. Determine affiliate code
            if payload.code:
                custom_code = payload.code.strip().upper()
                code_stmt = select(Affiliate).where(
                    Affiliate.code == custom_code,
                    Affiliate.isDeleted == False,
                )
                code_res = await self.db.execute(code_stmt)
                if code_res.scalars().first() is not None:
                    raise BadRequestException("The requested affiliate code is already taken")
                affiliate_code = custom_code
            else:
                affiliate_code = await self._generate_unique_affiliate_code(payload.name)

            # 7. Create Affiliate record
            affiliate = Affiliate(
                name=payload.name.strip(),
                email=email,
                code=affiliate_code,
                isSuspended=False,
            )
            self.db.add(affiliate)

            # 8. Mark invite as NOT ACTIVE upon verification
            invite.isActive = False

            await self.db.commit()
            await self.db.refresh(affiliate)

            # 9. Issue JWT access and refresh tokens
            token_payload = {
                "sub": str(affiliate.id),
                "email": affiliate.email,
                "name": affiliate.name,
                "code": affiliate.code,
                "role": "affiliate",
                "is_affiliate": True,
            }
            tokens_dict = create_access_token(token_payload)
            token_data = AffiliateTokenData(
                access_token=tokens_dict["access_token"],
                refresh_token=tokens_dict["refresh_token"],
            )

            # 10. Send welcome email
            try:
                send_email(
                    ResendPayload(
                        to=email,
                        subject="Welcome to Prefora Affiliate Program!",
                        html=f"""
                        Hi {affiliate.name},<br><br>
                        Congratulations! Your affiliate account on Prefora has been successfully created.<br><br>
                        Your unique referral code is: <h2>{affiliate.code}</h2>
                        Share this code or your referral links to start earning rewards.<br><br>
                        Best regards,<br>
                        The Prefora Team
                        """,
                    )
                )
            except Exception as mail_err:
                logger.error(f"Failed to send affiliate welcome email: {mail_err}")

            return ReturnType[AffiliateAuthResponse](
                success=True,
                message="Affiliate account created successfully",
                data=AffiliateAuthResponse(
                    tokens=token_data,
                    affiliate=AffiliateResponse.model_validate(affiliate),
                ),
            )
        except (BadRequestException, NotFoundException, UnauthorizedException, ForbiddenException):
            raise
        except Exception as e:
            logger.error(f"Error in register_affiliate: {e}")
            raise InternalServerException(str(e))

    async def login_affiliate(
        self,
        payload: AffiliateLoginRequest,
    ) -> ReturnType[MessageResponse | AffiliateAuthResponse]:
        """
        Initiates affiliate login:
        - If OTP code is not provided in payload: generates a 6-digit code, saves to OTP table, sends to email.
        - If OTP code is provided in payload: validates it immediately and returns tokens & affiliate details.
        """
        try:
            email = payload.email.strip().lower()

            stmt = select(Affiliate).where(
                Affiliate.email == email,
                Affiliate.isDeleted == False,
            )
            result = await self.db.execute(stmt)
            affiliate = result.scalars().first()

            if affiliate is None:
                raise BadRequestException("Affiliate with this email does not exist")

            if affiliate.isSuspended:
                raise ForbiddenException("Affiliate account is suspended. Please contact support.")

            # If OTP code was supplied directly in the login request, validate it immediately
            if payload.otp:
                return await self.validate_otp(
                    AffiliateValidateOtpRequest(email=email, otp=payload.otp)
                )

            # Otherwise, generate a 6-digit OTP code and send to email
            otp_code = f"{random.randint(100000, 999999)}"
            otp_entry = Otp(
                email=email,
                otp=otp_code,
                expires_at=datetime.now(timezone.utc) + timedelta(minutes=10),
                is_used=False,
            )
            self.db.add(otp_entry)
            await self.db.commit()

            try:
                send_email(
                    ResendPayload(
                        to=email,
                        subject="Your Prefora Affiliate Login Code",
                        html=f"""
                        Hi {affiliate.name},<br><br>
                        Your 6-digit verification code to sign in to the Prefora Affiliate Portal is:
                        <h2>{otp_code}</h2>
                        This code will expire in 10 minutes.<br><br>
                        If you did not request this code, please secure your account.
                        """,
                    )
                )
            except Exception as mail_err:
                logger.error(f"Failed to send affiliate login OTP email: {mail_err}")

            return ReturnType[MessageResponse](
                success=True,
                message="Verification code sent successfully to email",
                data=MessageResponse(message="Verification code sent successfully to email"),
            )
        except (BadRequestException, NotFoundException, UnauthorizedException, ForbiddenException):
            raise
        except Exception as e:
            logger.error(f"Error in login_affiliate: {e}")
            raise InternalServerException(str(e))

    async def validate_otp(
        self,
        payload: AffiliateValidateOtpRequest,
    ) -> ReturnType[AffiliateAuthResponse]:
        """
        Validates the 6-digit OTP code sent to affiliate email,
        and returns access token, refresh token, and affiliate details.
        """
        try:
            email = payload.email.strip().lower()
            code = payload.otp.strip()

            stmt = (
                select(Otp)
                .where(
                    Otp.email == email,
                    Otp.otp == code,
                    Otp.is_used == False,
                    Otp.isDeleted == False,
                )
                .order_by(Otp.created_at.desc())
            )
            result = await self.db.execute(stmt)
            otp_record = result.scalars().first()

            if otp_record is None:
                raise BadRequestException("Invalid or expired verification code")

            now = datetime.now(timezone.utc)
            expires_at = otp_record.expires_at
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=timezone.utc)

            if now > expires_at:
                raise BadRequestException("Verification code has expired")

            # Mark OTP as used
            otp_record.is_used = True
            await self.db.commit()

            # Retrieve affiliate record
            affiliate_stmt = select(Affiliate).where(
                Affiliate.email == email,
                Affiliate.isDeleted == False,
            )
            affiliate_res = await self.db.execute(affiliate_stmt)
            affiliate = affiliate_res.scalars().first()

            if affiliate is None:
                raise NotFoundException("Affiliate account not found")

            if affiliate.isSuspended:
                raise ForbiddenException("Affiliate account is suspended")

            # Generate tokens
            token_payload = {
                "sub": str(affiliate.id),
                "email": affiliate.email,
                "name": affiliate.name,
                "code": affiliate.code,
                "role": "affiliate",
                "is_affiliate": True,
            }
            tokens_dict = create_access_token(token_payload)
            token_data = AffiliateTokenData(
                access_token=tokens_dict["access_token"],
                refresh_token=tokens_dict["refresh_token"],
            )

            return ReturnType[AffiliateAuthResponse](
                success=True,
                message="Verification successful. Logged in.",
                data=AffiliateAuthResponse(
                    tokens=token_data,
                    affiliate=AffiliateResponse.model_validate(affiliate),
                ),
            )
        except (BadRequestException, NotFoundException, UnauthorizedException, ForbiddenException):
            raise
        except Exception as e:
            logger.error(f"Error in validate_otp: {e}")
            raise InternalServerException(str(e))

    async def refresh_token(
        self,
        payload: AffiliateRefreshTokenRequest,
    ) -> ReturnType[AffiliateTokenData]:
        """Refreshes affiliate access token using a valid refresh token."""
        try:
            token_payload = decode_token(payload.refresh_token)
            affiliate_id = token_payload.get("sub")
            token_type = token_payload.get("type")

            if not affiliate_id or token_type != "refresh":
                raise UnauthorizedException("Invalid refresh token")

            try:
                affiliate_uuid = uuid.UUID(str(affiliate_id))
            except (ValueError, TypeError):
                raise UnauthorizedException("Invalid affiliate ID in refresh token")

            stmt = select(Affiliate).where(
                Affiliate.id == affiliate_uuid,
                Affiliate.isDeleted == False,
            )
            result = await self.db.execute(stmt)
            affiliate = result.scalars().first()

            if affiliate is None:
                raise UnauthorizedException("Affiliate account not found")

            if affiliate.isSuspended:
                raise ForbiddenException("Affiliate account is suspended")

            new_tokens = create_access_token({
                "sub": str(affiliate.id),
                "email": affiliate.email,
                "name": affiliate.name,
                "code": affiliate.code,
                "role": "affiliate",
                "is_affiliate": True,
            })

            token_data = AffiliateTokenData(
                access_token=new_tokens["access_token"],
                refresh_token=new_tokens["refresh_token"],
            )

            return ReturnType[AffiliateTokenData](
                success=True,
                message="Token refreshed successfully",
                data=token_data,
            )
        except (BadRequestException, NotFoundException, UnauthorizedException, ForbiddenException):
            raise
        except Exception as e:
            logger.error(f"Error in refresh_token: {e}")
            raise InternalServerException(str(e))

    async def get_affiliate_by_id(
        self,
        affiliate_id: str | uuid.UUID,
    ) -> ReturnType[AffiliateResponse]:
        """Retrieves affiliate details by ID."""
        try:
            try:
                affiliate_uuid = (
                    uuid.UUID(str(affiliate_id))
                    if not isinstance(affiliate_id, uuid.UUID)
                    else affiliate_id
                )
            except (ValueError, TypeError):
                raise BadRequestException("Invalid affiliate ID format")

            stmt = select(Affiliate).where(
                Affiliate.id == affiliate_uuid,
                Affiliate.isDeleted == False,
            )
            result = await self.db.execute(stmt)
            affiliate = result.scalars().first()

            if affiliate is None:
                raise NotFoundException("Affiliate not found")

            return ReturnType[AffiliateResponse](
                success=True,
                message="Affiliate details retrieved successfully",
                data=AffiliateResponse.model_validate(affiliate),
            )
        except (BadRequestException, NotFoundException, UnauthorizedException, ForbiddenException):
            raise
        except Exception as e:
            logger.error(f"Error in get_affiliate_by_id: {e}")
            raise InternalServerException(str(e))

    async def get_all_affiliates(self) -> ReturnType[list[AffiliateResponse]]:
        """Admin helper: list all affiliates."""
        try:
            stmt = select(Affiliate).where(Affiliate.isDeleted == False).order_by(Affiliate.created_at.desc())
            result = await self.db.execute(stmt)
            affiliates = result.scalars().all()
            data = [AffiliateResponse.model_validate(a) for a in affiliates]
            return ReturnType[list[AffiliateResponse]](
                success=True,
                message="Affiliates retrieved successfully",
                data=data,
            )
        except Exception as e:
            logger.error(f"Error in get_all_affiliates: {e}")
            raise InternalServerException(str(e))

    async def get_all_invites(self) -> ReturnType[list[InviteResponse]]:
        """Admin helper: list all invites."""
        try:
            stmt = select(Invite).where(Invite.isDeleted == False).order_by(Invite.created_at.desc())
            result = await self.db.execute(stmt)
            invites = result.scalars().all()
            data = [
                InviteResponse(
                    id=i.id,
                    code=i.code,
                    email=i.email,
                    isActive=i.isActive,
                    endDate=i.endDate,
                    created_at=i.created_at,
                    updated_at=i.updated_at,
                )
                for i in invites
            ]
            return ReturnType[list[InviteResponse]](
                success=True,
                message="Invites retrieved successfully",
                data=data,
            )
        except Exception as e:
            logger.error(f"Error in get_all_invites: {e}")
            raise InternalServerException(str(e))


def get_affiliate_service(
    db: AsyncSession = Depends(get_db),
) -> AffiliateService:
    return AffiliateService(db)
