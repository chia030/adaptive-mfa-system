import jwt
from jose import JWTError
from datetime import datetime, timedelta
from typing import Optional
from shared_lib.config.settings import settings
from passlib.context import CryptContext

JWT_SECRET_KEY = settings.jwt_secret_key
JWT_ALGORITHM = settings.jwt_algorithm

def create_access_token(subject: str, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = {"sub": subject, "iat": datetime.now()}
    expire = datetime.now() + (expires_delta or timedelta(minutes=60)) # set exp time (default = 1h)
    to_encode.update({"exp": expire}) # add exp to token payload
    return jwt.encode(
        to_encode,
        JWT_SECRET_KEY,
        JWT_ALGORITHM
    )

def verify_access_token(token: str) -> dict:
    try:
        return jwt.decode(
                    token,
                    JWT_SECRET_KEY,
                    algorithms=[JWT_ALGORITHM],
                    options={"require_sub": True, "require_iat": True}
                )
    except JWTError:
        # return None if token is invalid or decoding fails
        return None

# pwd hashing context using Argon2
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")
