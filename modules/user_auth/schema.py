from pydantic import BaseModel
from enum import Enum
import uuid
from datetime import datetime

class Examination(str, Enum):
    waec = "waec"
    neco = "neco"
    utme = "utme"
    jamb = "jamb"


class CreateUser(BaseModel):
    first_name: str
    last_name: str
    email: str
    state: str
    university: str
    examinations: list[Examination]
    current_expectation: str


class UpdateUser(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    state: str | None = None
    university: str | None = None
    examinations: list[Examination] | None = None
    current_expectation: str | None = None


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


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class UserResponse(BaseModel):
    id: uuid.UUID
    first_name: str
    last_name: str
    email: str
    state: str
    university: str
    examinations: list[Examination]
    current_expectation: str
    prep_points: int
    best_score: int

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
