from jose import JWTError, jwt
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from app.db.models import User
from app.db.database import AsyncSessionLocal
from sqlalchemy.future import select
from app.core.redis import redis

load_dotenv()

# secret key loaded from the environment variable
SECRET_KEY = os.getenv("SECRET_KEY") # fallback secret key in 2nd arg, used if the env variable is not set
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 # default expiration

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login") # match login route

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

# validate token and check user email
async def get_current_user(token: str = Depends(oauth2_scheme)):
    # check if token is blacklisted
    blacklist_key = f"bl:{token}"
    blacklisted = await redis.get(blacklist_key)
    if blacklisted:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has been revoked")
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        # load user from database? e.g. payload.get("sub") to get user email
        email: str = payload.get("sub")
        if email is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate credentials")
        
        # check db for user | db operations are async
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(User).where(User.email == email))
            user = result.scalar_one_or_none()
            if user is None:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    
    return user # should include current token

# validate admin user    
async def admin_required(current_user: User = Depends(get_current_user)):
    if current_user.role.lower() != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin privileges required")
    return current_user
