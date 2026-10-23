from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict, EmailStr, Field


class SendInviteRequest(BaseModel):
    email: EmailStr
    invite_url: str | None = Field(
        default=None,
        description="Optional base URL for registration link. Defaults to configured frontend URL."
    )


class InviteResponse(BaseModel):
    id: UUID
    code: str
    email: str
    isActive: bool
    endDate: datetime
    invite_link: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class AffiliateRegisterRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    email: EmailStr
    invite_code: str = Field(..., min_length=6, max_length=6, description="6-digit unique invite code")


class AffiliateLoginRequest(BaseModel):
    email: EmailStr


class AffiliateValidateOtpRequest(BaseModel):
    email: EmailStr
    otp: str = Field(..., min_length=6, max_length=6, description="6-digit OTP code sent to email")


class AffiliateRefreshTokenRequest(BaseModel):
    refresh_token: str


class AffiliateTokenData(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class AffiliateResponse(BaseModel):
    id: UUID
    name: str
    email: str
    code: str
    isSuspended: bool
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class AffiliateAuthResponse(BaseModel):
    tokens: AffiliateTokenData
    affiliate: AffiliateResponse


class MessageResponse(BaseModel):
    message: str
