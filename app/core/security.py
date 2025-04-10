from jose import JWTError, jwt
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

load_dotenv()

# secret key loaded from the environment variable
SECRET_KEY = os.getenv("SECRET_KEY") # fallback secret key in 2nd arg, used if the env variable is not set
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 # default expiration

def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()  # copy data to avoid modifying the original
    # set expiration time
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})  # add expiration to token payload

    # mfa flag
    if "mfa" not in to_encode:
        to_encode["mfa"] = False

    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        # returns None if token is invalid or decoding fails
        return None

#TODO: find a better alternative for datetime.utcnow()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login") # match login route

# validate token and check user email
async def get_current_user(token: str = Depends(oauth2_scheme)):
    from jose import JWTError, jwt
    from app.db.database import AsyncSessionLocal
    from app.db.models import User
    from sqlalchemy.future import select

    # could be invalid credentials or decoding error
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
    )

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    # db operations are async
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        if user is None:
            raise credentials_exception
        return user
