from fastapi import security
from common.constants.constant import ACCESS_TOKEN_EXPIRATION_TIME, ALGORITHM
from datetime import datetime, timedelta, timezone
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import os
from common.exceptions.unauthorized_exception import UnauthorizedException 

SECRET_KEY = os.getenv("SECRET_KEY")

class Access_Token_Creation_Return:
    access_token: str | None
    refresh_token: str | None

def create_access_token(data: dict) -> Access_Token_Creation_Return:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRATION_TIME)
    ### for refresh token
    refresh_token_expiry = datetime.now(timezone.utc) + timedelta(days=7)
    
    to_encode["exp"] = expire
    token = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    to_encode['exp'] = refresh_token_expiry
    refresh_token = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return {"access_token": token, "refresh_token": refresh_token}
    
def verify_access_token(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
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
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )