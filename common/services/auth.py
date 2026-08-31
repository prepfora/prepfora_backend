from common.constants.constant import ACCESS_TOKEN_EXPIRATION_TIME, ALGORITHM
from datetime import datetime, timedelta, timezone
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import os
from common.exceptions.unauthorized_exception import UnauthorizedException 

SECRET_KEY = os.getenv("SECRET_KEY", "prefora_default_secret_key_2026")
security = HTTPBearer()


class Access_Token_Creation_Return:
    access_token: str | None
    refresh_token: str | None


def create_access_token(data: dict) -> dict:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRATION_TIME)
    refresh_token_expiry = datetime.now(timezone.utc) + timedelta(days=7)
    
    to_encode["exp"] = expire
    token = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    
    refresh_payload = data.copy()
    refresh_payload["exp"] = refresh_token_expiry
    refresh_payload["type"] = "refresh"
    refresh_token = jwt.encode(refresh_payload, SECRET_KEY, algorithm=ALGORITHM)
    return {"access_token": token, "refresh_token": refresh_token}


def decode_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        raise UnauthorizedException("Invalid or expired token")


def verify_access_token(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> dict:
    token = credentials.credentials
    try:
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM]
        )

        user_id = payload.get("sub")

        if user_id is None:
            raise UnauthorizedException("Invalid token")

        return payload

    except JWTError:
        raise UnauthorizedException("Invalid or expired token")