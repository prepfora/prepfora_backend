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
    code: str | None = Field(default=None, description="Optional custom referral code")


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
    code: str | None = None
    isSuspended: bool
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class AffiliateAuthResponse(BaseModel):
    tokens: AffiliateTokenData
    affiliate: AffiliateResponse


class MessageResponse(BaseModel):
    message: str


class AffiliateAnalyticsResponse(BaseModel):
    total_referrals: int = Field(..., description="Total number of users referred by this affiliate")
    total_referred: int = Field(..., description="Alias for total_referrals")
    referrals_today: int = Field(0, description="Users referred in the last 24 hours")
    referrals_this_week: int = Field(0, description="Users referred in the last 7 days")
    referrals_this_month: int = Field(0, description="Users referred in the last 30 days")
    affiliate_id: UUID = Field(..., description="Affiliate ID")
    affiliate_name: str = Field(..., description="Affiliate name")
    affiliate_code: str = Field(..., description="Affiliate referral code")

    model_config = ConfigDict(from_attributes=True)


class ReferredUserResponse(BaseModel):
    id: UUID
    first_name: str | None = None
    last_name: str | None = None
    email: str
    phone: str | None = None
    state: str | None = None
    university: str | None = None
    examinations: list[str] | None = None
    prep_points: int | None = 0
    best_score: int | None = 0
    profile_picture: str | None = None
    referral_code: str | None = None
    created_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)
