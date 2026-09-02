import random
import uuid
import httpx
from datetime import datetime, timedelta, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from common.classes.return_type import ReturnType
from common.database import get_db
from common.exceptions.bad_request_exception import BadRequestException
from common.exceptions.not_found_expection import NotFoundException
from common.exceptions.unauthorized_exception import UnauthorizedException
from common.exceptions.internal_server_exception import InternalServerException
from common.logger import logger
from common.services.auth import create_access_token, decode_token
from common.services.emaill_service import send_email, ResendPayload
from fastapi import Depends

from models.user_model import User
from models.otp_model import Otp
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


class UserService:
    db: AsyncSession

    def __init__(self, db: AsyncSession):
        self.db = db

    async def register_user(self, payload: CreateUser) -> ReturnType[UserResponse]:
        try:
            email = payload.email.strip().lower()

            # Check if user already exists
            stmt = select(User).where(User.email == email, User.isDeleted == False)
            result = await self.db.execute(stmt)
            existing_user = result.scalars().first()
            if existing_user is not None:
                raise BadRequestException("User with this email already exists")

            # Create User
            user = User(
              
                email=email,
                
            )
            self.db.add(user)
            await self.db.commit()
            await self.db.refresh(user)

            # Generate OTP
            otp_code = f"{random.randint(100000, 999999)}"
            otp_entry = Otp(
                email=email,
                otp=otp_code,
                expires_at=datetime.now(timezone.utc) + timedelta(minutes=10),
                is_used=False,
            )
            self.db.add(otp_entry)
            await self.db.commit()

            # Send OTP email
            try:
                send_email(
                    ResendPayload(
                        to=email,
                        subject="Your Prefora Verification Code",
                        html=f"Hi {payload.email},<br><br>Your verification code for Prefora is: <h2>{otp_code}</h2>It will expire in 10 minutes.",
                    )
                )
            except Exception as mail_err:
                logger.error("Failed to send OTP email during registration: " + str(mail_err))

            return ReturnType[UserResponse](
                success=True,
                message="User registered successfully. Verification OTP sent to email.",
                data=UserResponse.model_validate(user),
            )
        except (BadRequestException, NotFoundException, UnauthorizedException):
            raise
        except Exception as e:
            logger.error("Error in register_user: " + str(e))
            raise InternalServerException(str(e))

    async def login_user(self, payload: LoginRequest) -> ReturnType[MessageResponse]:
        try:
            email = payload.email.strip().lower()

            # Verify user exists
            stmt = select(User).where(User.email == email, User.isDeleted == False)
            result = await self.db.execute(stmt)
            user = result.scalars().first()
            if user is None:
                raise BadRequestException("User with this email does not exist")

            # Generate OTP
            otp_code = f"{random.randint(100000, 999999)}"
            otp_entry = Otp(
                email=email,
                otp=otp_code,
                expires_at=datetime.now(timezone.utc) + timedelta(minutes=10),
                is_used=False,
            )
            self.db.add(otp_entry)
            await self.db.commit()

            # Send OTP email
            try:
                send_email(
                    ResendPayload(
                        to=email,
                        subject="Your Prefora Login Verification Code",
                        html=f"Hi {user.first_name},<br><br>Your login code for Prefora is: <h2>{otp_code}</h2>It will expire in 10 minutes.",
                    )
                )
            except Exception as mail_err:
                logger.error("Failed to send login OTP email: " + str(mail_err))

            return ReturnType[MessageResponse](
                success=True,
                message="OTP sent successfully to email",
                data=MessageResponse(message="OTP sent successfully"),
            )
        except (BadRequestException, NotFoundException, UnauthorizedException):
            raise
        except Exception as e:
            logger.error("Error in login_user: " + str(e))
            raise InternalServerException(str(e))

    async def validate_otp(self, payload: ValidateOtpRequest) -> ReturnType[AuthTokenResponse]:
        try:
            email = payload.email.strip().lower()
            code = payload.otp.strip()

            stmt = (
                select(Otp)
                .where(Otp.email == email, Otp.otp == code, Otp.is_used == False, Otp.isDeleted == False)
                .order_by(Otp.created_at.desc())
            )
            result = await self.db.execute(stmt)
            otp_record = result.scalars().first()

            if otp_record is None:
                raise BadRequestException("Invalid or expired OTP")

            now = datetime.now(timezone.utc)
            expires_at = otp_record.expires_at
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=timezone.utc)

            if now > expires_at:
                raise BadRequestException("OTP has expired")

            # Mark OTP as used
            otp_record.is_used = True
            await self.db.commit()

            # Get user details
            user_stmt = select(User).where(User.email == email, User.isDeleted == False)
            user_result = await self.db.execute(user_stmt)
            user = user_result.scalars().first()

            if user is None:
                raise NotFoundException("User account not found")

            # Generate tokens
            tokens_dict = create_access_token({"sub": str(user.id), "email": user.email})
            token_data = TokenData(
                access_token=tokens_dict["access_token"],
                refresh_token=tokens_dict["refresh_token"],
            )

            return ReturnType[AuthTokenResponse](
                success=True,
                message="OTP validated successfully",
                data=AuthTokenResponse(
                    tokens=token_data,
                    user=UserResponse.model_validate(user),
                ),
            )
        except (BadRequestException, NotFoundException, UnauthorizedException):
            raise
        except Exception as e:
            logger.error("Error in validate_otp: " + str(e))
            raise InternalServerException(str(e))

    async def google_auth(self, payload: GoogleAuthRequest) -> ReturnType[AuthTokenResponse]:
        try:
            email = payload.email.strip().lower() if payload.email else None
            first_name = payload.first_name or "Google User"
            last_name = payload.last_name or ""

            # If id_token is provided, attempt Google token validation
            if payload.id_token:
                try:
                    async with httpx.AsyncClient() as client:
                        resp = await client.get(
                            "https://oauth2.googleapis.com/tokeninfo",
                            params={"id_token": payload.id_token},
                            timeout=10.0,
                        )
                        if resp.status_code == 200:
                            data = resp.json()
                            if "email" in data:
                                email = data["email"].strip().lower()
                            if "given_name" in data:
                                first_name = data["given_name"]
                            if "family_name" in data:
                                last_name = data["family_name"]
                except Exception as g_err:
                    logger.error("Google token verification exception: " + str(g_err))

            if not email:
                raise BadRequestException("Email is required for Google authentication")

            # Check if user exists
            stmt = select(User).where(User.email == email, User.isDeleted == False)
            result = await self.db.execute(stmt)
            user = result.scalars().first()

            if user is None:
                # Create user
                user = User(
                    first_name=first_name,
                    last_name=last_name,
                    email=email,
                    state=payload.state or "",
                    university=payload.university or "",
                    examinations=payload.examinations or [],
                    current_expectation=payload.current_expectation or "",
                    prep_points=0,
                    best_score=0,
                )
                self.db.add(user)
                await self.db.commit()
                await self.db.refresh(user)

            # Generate tokens
            tokens_dict = create_access_token({"sub": str(user.id), "email": user.email})
            token_data = TokenData(
                access_token=tokens_dict["access_token"],
                refresh_token=tokens_dict["refresh_token"],
            )

            return ReturnType[AuthTokenResponse](
                success=True,
                message="Google authentication successful",
                data=AuthTokenResponse(
                    tokens=token_data,
                    user=UserResponse.model_validate(user),
                ),
            )
        except (BadRequestException, NotFoundException, UnauthorizedException):
            raise
        except Exception as e:
            logger.error("Error in google_auth: " + str(e))
            raise InternalServerException(str(e))

    async def refresh_token(self, payload: RefreshTokenRequest) -> ReturnType[TokenData]:
        try:
            token_payload = decode_token(payload.refresh_token)
            user_id = token_payload.get("sub")

            if not user_id:
                raise UnauthorizedException("Invalid refresh token payload")

            stmt = select(User).where(User.id == uuid.UUID(user_id), User.isDeleted == False)
            result = await self.db.execute(stmt)
            user = result.scalars().first()

            if user is None:
                raise UnauthorizedException("User not found")

            tokens_dict = create_access_token({"sub": str(user.id), "email": user.email})
            token_data = TokenData(
                access_token=tokens_dict["access_token"],
                refresh_token=tokens_dict["refresh_token"],
            )

            return ReturnType[TokenData](
                success=True,
                message="Token refreshed successfully",
                data=token_data,
            )
        except (BadRequestException, NotFoundException, UnauthorizedException):
            raise
        except Exception as e:
            logger.error("Error in refresh_token: " + str(e))
            raise InternalServerException(str(e))

    async def get_current_user_details(self, user_id: str) -> ReturnType[UserResponse]:
        try:
            stmt = select(User).where(User.id == uuid.UUID(user_id), User.isDeleted == False)
            result = await self.db.execute(stmt)
            user = result.scalars().first()

            if user is None:
                raise NotFoundException("User not found")

            return ReturnType[UserResponse](
                success=True,
                message="User details fetched successfully",
                data=UserResponse.model_validate(user),
            )
        except (BadRequestException, NotFoundException, UnauthorizedException):
            raise
        except Exception as e:
            logger.error("Error in get_current_user_details: " + str(e))
            raise InternalServerException(str(e))

    async def update_user_details(self, user_id: str, payload: UpdateUser) -> ReturnType[UserResponse]:
        try:
            stmt = select(User).where(User.id == uuid.UUID(user_id), User.isDeleted == False)
            result = await self.db.execute(stmt)
            user = result.scalars().first()

            if user is None:
                raise NotFoundException("User not found")

            if payload.first_name is not None:
                user.first_name = payload.first_name
            if payload.last_name is not None:
                user.last_name = payload.last_name
            if payload.state is not None:
                user.state = payload.state
            if payload.university is not None:
                user.university = payload.university
            if payload.examinations is not None:
                user.examinations = payload.examinations
            if payload.current_expectation is not None:
                user.current_expectation = payload.current_expectation

            await self.db.commit()
            await self.db.refresh(user)

            return ReturnType[UserResponse](
                success=True,
                message="User details updated successfully",
                data=UserResponse.model_validate(user),
            )
        except (BadRequestException, NotFoundException, UnauthorizedException):
            raise
        except Exception as e:
            logger.error("Error in update_user_details: " + str(e))
            raise InternalServerException(str(e))


def get_user_service(
    db: AsyncSession = Depends(get_db),
) -> UserService:
    return UserService(db)
