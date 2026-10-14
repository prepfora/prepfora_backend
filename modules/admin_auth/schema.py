from pydantic import BaseModel, ConfigDict
from datetime import datetime
import uuid


class AdminLoginRequest(BaseModel):
    email: str


class AdminRegisterRequest(BaseModel):
    email: str
    name: str
    role_id: uuid.UUID | None = None
    profile_picture: str | None = None


class CreateAdminRequest(BaseModel):
    email: str
    name: str
    role_id: uuid.UUID | None = None
    profile_picture: str | None = None
    is_active: bool = True


class AdminValidateOtpRequest(BaseModel):
    email: str
    otp: str


class AdminRefreshTokenRequest(BaseModel):
    refresh_token: str


class AdminVerifyTokenRequest(BaseModel):
    token: str | None = None


class UpdateAdminProfile(BaseModel):
    name: str | None = None
    profile_picture: str | None = None


class AdminRoleResponse(BaseModel):
    id: uuid.UUID
    name: str
    permissions: list[str] = []

    model_config = ConfigDict(from_attributes=True)


class AdminResponse(BaseModel):
    id: uuid.UUID
    email: str
    name: str
    role_id: uuid.UUID
    role: AdminRoleResponse | None = None
    profile_picture: str | None = None
    is_active: bool
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class AdminTokenData(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class AdminAuthResponse(BaseModel):
    tokens: AdminTokenData
    admin: AdminResponse


class MessageResponse(BaseModel):
    message: str
