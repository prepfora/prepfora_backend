import random
import uuid
from datetime import datetime, timedelta, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import Depends

from common.classes.return_type import ReturnType
from common.database import get_db
from common.exceptions.bad_request_exception import BadRequestException
from common.exceptions.not_found_expection import NotFoundException
from common.exceptions.unauthorized_exception import UnauthorizedException
from common.exceptions.internal_server_exception import InternalServerException
from common.logger import logger
from common.services.auth import create_access_token, decode_token
from common.services.emaill_service import send_email, ResendPayload

from models.admin_model import Admin
from models.admin_role_model import Admin_Role, Permission
from models.otp_model import Otp
from modules.admin_auth.schema import (
    AdminLoginRequest,
    AdminRegisterRequest,
    CreateAdminRequest,
    AdminValidateOtpRequest,
    AdminRefreshTokenRequest,
    AdminRoleResponse,
    AdminResponse,
    AdminTokenData,
    AdminAuthResponse,
    MessageResponse,
    UpdateAdminProfile,
)


class AdminAuthService:
    db: AsyncSession

    def __init__(self, db: AsyncSession):
        self.db = db

    async def _get_admin_role(self, role_id: uuid.UUID) -> AdminRoleResponse | None:
        """Fetch role details by role_id."""
        try:
            stmt = select(Admin_Role).where(
                Admin_Role.id == role_id,
                Admin_Role.isDeleted == False,
            )
            result = await self.db.execute(stmt)
            role = result.scalars().first()
            if not role:
                return None

            permissions_list = [
                p.value if hasattr(p, "value") else str(p)
                for p in (role.permissions or [])
            ]
            return AdminRoleResponse(
                id=role.id,
                name=role.name,
                permissions=permissions_list,
            )
        except Exception as e:
            logger.error(f"Error fetching admin role: {e}")
            return None

    async def _get_or_create_default_role(self) -> Admin_Role:
        """Gets existing default role or creates a default Admin role if none exists."""
        stmt = select(Admin_Role).where(
            Admin_Role.name.in_(["Admin", "Super Admin"]),
            Admin_Role.isDeleted == False,
        )
        result = await self.db.execute(stmt)
        role = result.scalars().first()
        if role:
            return role

        default_role = Admin_Role(
            name="Admin",
            permissions=[
                Permission.OVERVIEW,
                Permission.USERS,
                Permission.ADMINS,
                Permission.QUESTION,
            ],
        )
        self.db.add(default_role)
        await self.db.commit()
        await self.db.refresh(default_role)
        return default_role

    async def _build_admin_response(self, admin: Admin) -> AdminResponse:
        """Assembles AdminResponse with associated role."""
        role_data = await self._get_admin_role(admin.role_id)
        return AdminResponse(
            id=admin.id,
            email=admin.email,
            name=admin.name,
            role_id=admin.role_id,
            role=role_data,
            profile_picture=admin.profile_picture,
            is_active=admin.is_active,
            created_at=admin.created_at,
            updated_at=admin.updated_at,
        )

    async def create_admin(self, payload: CreateAdminRequest) -> ReturnType[AdminResponse]:
        """Creates a new admin account directly without requiring immediate OTP validation."""
        try:
            email = payload.email.strip().lower()

            # Check if admin already exists
            stmt = select(Admin).where(
                Admin.email == email,
                Admin.isDeleted == False,
            )
            result = await self.db.execute(stmt)
            existing_admin = result.scalars().first()
            if existing_admin is not None:
                raise BadRequestException("Admin with this email already exists")

            # Determine role
            if payload.role_id:
                role_stmt = select(Admin_Role).where(
                    Admin_Role.id == payload.role_id,
                    Admin_Role.isDeleted == False,
                )
                role_res = await self.db.execute(role_stmt)
                role_record = role_res.scalars().first()
                if not role_record:
                    raise BadRequestException("Specified role does not exist")
                role_id = role_record.id
            else:
                default_role = await self._get_or_create_default_role()
                role_id = default_role.id

            admin = Admin(
                email=email,
                name=payload.name.strip(),
                role_id=role_id,
                profile_picture=payload.profile_picture,
                is_active=payload.is_active,
            )
            self.db.add(admin)
            await self.db.commit()
            await self.db.refresh(admin)

            # Send welcome email notification
            try:
                send_email(
                    ResendPayload(
                        to=email,
                        subject="Welcome to Prefora Admin",
                        html=f"Hi {admin.name},<br><br>Your administrator account has been created on Prefora. You can sign in using passwordless authentication with this email.",
                    )
                )
            except Exception as mail_err:
                logger.error(f"Failed to send admin creation welcome email: {mail_err}")

            admin_data = await self._build_admin_response(admin)
            return ReturnType[AdminResponse](
                success=True,
                message="Admin created successfully",
                data=admin_data,
            )
        except (BadRequestException, NotFoundException, UnauthorizedException):
            raise
        except Exception as e:
            logger.error(f"Error in create_admin: {e}")
            raise InternalServerException(str(e))

    async def register_admin(self, payload: AdminRegisterRequest) -> ReturnType[AdminResponse]:
        """Registers a new admin and sends a verification OTP to their email."""
        try:
            email = payload.email.strip().lower()

            # Check if admin already exists
            stmt = select(Admin).where(
                Admin.email == email,
                Admin.isDeleted == False,
            )
            result = await self.db.execute(stmt)
            existing_admin = result.scalars().first()
            if existing_admin is not None:
                raise BadRequestException("Admin with this email already exists")

            # Determine role
            if payload.role_id:
                role_stmt = select(Admin_Role).where(
                    Admin_Role.id == payload.role_id,
                    Admin_Role.isDeleted == False,
                )
                role_res = await self.db.execute(role_stmt)
                role_record = role_res.scalars().first()
                if not role_record:
                    raise BadRequestException("Specified role does not exist")
                role_id = role_record.id
            else:
                default_role = await self._get_or_create_default_role()
                role_id = default_role.id

            admin = Admin(
                email=email,
                name=payload.name.strip(),
                role_id=role_id,
                profile_picture=payload.profile_picture,
                is_active=True,
            )
            self.db.add(admin)
            await self.db.commit()
            await self.db.refresh(admin)

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
                        subject="Your Prefora Admin Verification Code",
                        html=f"Hi {admin.name},<br><br>Your verification code for Prefora Admin is: <h2>{otp_code}</h2>It will expire in 10 minutes.",
                    )
                )
            except Exception as mail_err:
                logger.error(f"Failed to send admin registration OTP email: {mail_err}")

            admin_data = await self._build_admin_response(admin)
            return ReturnType[AdminResponse](
                success=True,
                message="Admin registered successfully. Verification OTP sent to email.",
                data=admin_data,
            )
        except (BadRequestException, NotFoundException, UnauthorizedException):
            raise
        except Exception as e:
            logger.error(f"Error in register_admin: {e}")
            raise InternalServerException(str(e))

    async def login_admin(self, payload: AdminLoginRequest) -> ReturnType[MessageResponse]:
        """Initiates passwordless login for admin by sending OTP to their email."""
        try:
            email = payload.email.strip().lower()

            stmt = select(Admin).where(
                Admin.email == email,
                Admin.isDeleted == False,
            )
            result = await self.db.execute(stmt)
            admin = result.scalars().first()

            if admin is None:
                raise BadRequestException("Admin with this email does not exist")

            if not admin.is_active:
                raise UnauthorizedException("Admin account is deactivated. Please contact support.")

            # Generate OTP
            otp_code = f"{random.randint(100000, 999999)}"
            otp_entry = Otp(
                email=email,
                otp=otp_code,
                expires_at=datetime.now(timezone.utc) + timedelta(minutes=30),
                is_used=False,
            )
            self.db.add(otp_entry)
            await self.db.commit()

            # Send OTP email
            try:
                send_email(
                    ResendPayload(
                        to=email,
                        subject="Your Prefora Admin Login Verification Code",
                        html=f"Hi {admin.name},<br><br>Your login code for Prefora Admin is: <h2>{otp_code}</h2>It will expire in 10 minutes.",
                    )
                )
            except Exception as mail_err:
                logger.error(f"Failed to send admin login OTP email: {mail_err}")

            return ReturnType[MessageResponse](
                success=True,
                message="OTP sent successfully to email",
                data=MessageResponse(message="OTP sent successfully to email"),
            )
        except (BadRequestException, NotFoundException, UnauthorizedException):
            raise
        except Exception as e:
            logger.error(f"Error in login_admin: {e}")
            raise InternalServerException(str(e))

    async def validate_otp(self, payload: AdminValidateOtpRequest) -> ReturnType[AdminAuthResponse]:
        """Validates the OTP sent to admin, issues access and refresh tokens."""
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

            # Fetch Admin record
            admin_stmt = select(Admin).where(
                Admin.email == email,
                Admin.isDeleted == False,
            )
            admin_result = await self.db.execute(admin_stmt)
            admin = admin_result.scalars().first()

            if admin is None:
                raise NotFoundException("Admin account not found")

            if not admin.is_active:
                raise UnauthorizedException("Admin account is deactivated")

            # Fetch Role for token claims
            role_data = await self._get_admin_role(admin.role_id)
            role_name = role_data.name if role_data else "admin"

            # Generate tokens with admin claims
            token_payload = {
                "sub": str(admin.id),
                "email": admin.email,
                "name": admin.name,
                "role": role_name,
                "role_id": str(admin.role_id),
                "is_admin": True,
            }
            tokens_dict = create_access_token(token_payload)
            token_data = AdminTokenData(
                access_token=tokens_dict["access_token"],
                refresh_token=tokens_dict["refresh_token"],
            )

            admin_data = await self._build_admin_response(admin)

            return ReturnType[AdminAuthResponse](
                success=True,
                message="OTP validated successfully",
                data=AdminAuthResponse(
                    tokens=token_data,
                    admin=admin_data,
                ),
            )
        except (BadRequestException, NotFoundException, UnauthorizedException):
            raise
        except Exception as e:
            logger.error(f"Error in validate_otp: {e}")
            raise InternalServerException(str(e))

    async def verify_token(self, token: str) -> ReturnType[AdminResponse]:
        """Verifies JWT token validity and confirms active admin identity."""
        try:
            payload = decode_token(token)
            admin_id = payload.get("sub")

            if not admin_id:
                raise UnauthorizedException("Invalid token payload")

            try:
                admin_uuid = uuid.UUID(str(admin_id))
            except (ValueError, TypeError):
                raise UnauthorizedException("Invalid admin ID in token")

            stmt = select(Admin).where(
                Admin.id == admin_uuid,
                Admin.isDeleted == False,
            )
            result = await self.db.execute(stmt)
            admin = result.scalars().first()

            if admin is None:
                raise UnauthorizedException("Admin account not found")

            if not admin.is_active:
                raise UnauthorizedException("Admin account is inactive")

            admin_data = await self._build_admin_response(admin)
            return ReturnType[AdminResponse](
                success=True,
                message="Token is valid",
                data=admin_data,
            )
        except (BadRequestException, NotFoundException, UnauthorizedException):
            raise
        except Exception as e:
            logger.error(f"Error in verify_token: {e}")
            raise UnauthorizedException("Invalid or expired token")

    async def refresh_token(self, payload: AdminRefreshTokenRequest) -> ReturnType[AdminTokenData]:
        """Refreshes admin access token using a valid refresh token."""
        try:
            token_payload = decode_token(payload.refresh_token)
            admin_id = token_payload.get("sub")
            token_type = token_payload.get("type")

            if not admin_id or token_type != "refresh":
                raise UnauthorizedException("Invalid refresh token")

            try:
                admin_uuid = uuid.UUID(str(admin_id))
            except (ValueError, TypeError):
                raise UnauthorizedException("Invalid admin ID in refresh token")

            stmt = select(Admin).where(
                Admin.id == admin_uuid,
                Admin.isDeleted == False,
            )
            result = await self.db.execute(stmt)
            admin = result.scalars().first()

            if admin is None:
                raise UnauthorizedException("Admin account not found")

            if not admin.is_active:
                raise UnauthorizedException("Admin account is inactive")

            role_data = await self._get_admin_role(admin.role_id)
            role_name = role_data.name if role_data else "admin"

            tokens_dict = create_access_token({
                "sub": str(admin.id),
                "email": admin.email,
                "name": admin.name,
                "role": role_name,
                "role_id": str(admin.role_id),
                "is_admin": True,
            })
            token_data = AdminTokenData(
                access_token=tokens_dict["access_token"],
                refresh_token=tokens_dict["refresh_token"],
            )

            return ReturnType[AdminTokenData](
                success=True,
                message="Token refreshed successfully",
                data=token_data,
            )
        except (BadRequestException, NotFoundException, UnauthorizedException):
            raise
        except Exception as e:
            logger.error(f"Error in refresh_token: {e}")
            raise InternalServerException(str(e))

    async def get_current_admin_details(self, admin_id: str) -> ReturnType[AdminResponse]:
        """Retrieves profile and role details of currently authenticated admin."""
        try:
            try:
                admin_uuid = uuid.UUID(str(admin_id))
            except (ValueError, TypeError):
                raise BadRequestException("Invalid admin ID")

            stmt = select(Admin).where(
                Admin.id == admin_uuid,
                Admin.isDeleted == False,
            )
            result = await self.db.execute(stmt)
            admin = result.scalars().first()

            if admin is None:
                raise NotFoundException("Admin not found")

            if not admin.is_active:
                raise UnauthorizedException("Admin account is inactive")

            admin_data = await self._build_admin_response(admin)
            return ReturnType[AdminResponse](
                success=True,
                message="Admin details fetched successfully",
                data=admin_data,
            )
        except (BadRequestException, NotFoundException, UnauthorizedException):
            raise
        except Exception as e:
            logger.error(f"Error in get_current_admin_details: {e}")
            raise InternalServerException(str(e))

    async def update_current_admin_details(
        self,
        admin_id: str,
        payload: UpdateAdminProfile,
    ) -> ReturnType[AdminResponse]:
        """Updates profile details for currently authenticated admin."""
        try:
            try:
                admin_uuid = uuid.UUID(str(admin_id))
            except (ValueError, TypeError):
                raise BadRequestException("Invalid admin ID")

            stmt = select(Admin).where(
                Admin.id == admin_uuid,
                Admin.isDeleted == False,
            )
            result = await self.db.execute(stmt)
            admin = result.scalars().first()

            if admin is None:
                raise NotFoundException("Admin not found")

            if not admin.is_active:
                raise UnauthorizedException("Admin account is inactive")

            if payload.name is not None:
                admin.name = payload.name.strip()
            if payload.profile_picture is not None:
                admin.profile_picture = payload.profile_picture

            await self.db.commit()
            await self.db.refresh(admin)

            admin_data = await self._build_admin_response(admin)
            return ReturnType[AdminResponse](
                success=True,
                message="Admin details updated successfully",
                data=admin_data,
            )
        except (BadRequestException, NotFoundException, UnauthorizedException):
            raise
        except Exception as e:
            logger.error(f"Error in update_current_admin_details: {e}")
            raise InternalServerException(str(e))


def get_admin_service(
    db: AsyncSession = Depends(get_db),
) -> AdminAuthService:
    return AdminAuthService(db)
