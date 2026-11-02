from pydantic import BaseModel, Field, AliasChoices
from enum import Enum
import uuid
from datetime import datetime


class Examination(str, Enum):
    waec = "waec"
    neco = "neco"
    utme = "utme"
    jamb = "jamb"


class CreateUser(BaseModel):
    email: str
    referral_code: str | None = Field(default=None, validation_alias=AliasChoices("referral_code", "referralCode"))


class UpdateUser(BaseModel):
    first_name: str | None = Field(default=None, validation_alias=AliasChoices("first_name", "firstName"))
    last_name: str | None = Field(default=None, validation_alias=AliasChoices("last_name", "lastName"))
    state: str | None = None
    university: str | None = None
    examinations: list[Examination] | None = None
    current_expectation: str | None = Field(default=None, validation_alias=AliasChoices("current_expectation", "currentExpectation"))
    phone: str | None = None
    current_examination_date: str | None = Field(default=None, validation_alias=AliasChoices("current_examination_date", "currentExaminationDate"))
    profile_picture: str | None = Field(default=None, validation_alias=AliasChoices("profile_picture", "profilePicture"))
    referral_code: str | None = Field(default=None, validation_alias=AliasChoices("referral_code", "referralCode"))



class LoginRequest(BaseModel):
    email: str


class ValidateOtpRequest(BaseModel):
    email: str
    otp: str


class GoogleAuthRequest(BaseModel):
    id_token: str | None = None
    email: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    state: str | None = None
    university: str | None = None
    examinations: list[Examination] | None = None
    current_expectation: str | None = None
    phone: str | None = None
    current_examination_date: str | None = None
    profile_picture: str | None = None
    affiliate_code: str | None = None
    referral_code: str | None = None



class RefreshTokenRequest(BaseModel):
    refresh_token: str


class UserResponse(BaseModel):
    id: uuid.UUID
    first_name: str | None = None
    last_name: str | None = None
    email: str
    state: str | None = None
    phone: str | None = None
    current_examination_date: str | None = None
    university: str | None = None
    examinations: list[Examination] | None = None
    current_expectation: str | None = None
    prep_points: int | None = 0
    best_score: int | None = 0
    profile_picture: str | None = None
    referral_code: str | None = None


    class Config:
        from_attributes = True


class TokenData(BaseModel):
    access_token: str
    refresh_token: str


class AuthTokenResponse(BaseModel):
    tokens: TokenData
    user: UserResponse


class MessageResponse(BaseModel):
    message: str
