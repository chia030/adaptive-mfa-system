from fastapi.security import OAuth2PasswordBearer
from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from jose import jwt, JWTError
from shared_lib.infrastructure.db import get_auth_db
from shared_lib.infrastructure.cache import get_auth_redis
from shared_lib.config.settings import settings
from app.db.models import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login")
redis = get_auth_redis()

async def get_current_user(token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_auth_db)):
    # check if token is blacklisted
    blacklist_key = f"bl:{token}"
    blacklisted = await redis.get(blacklist_key)
    if blacklisted:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has been revoked")
    
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        # load user from database? e.g. payload.get("sub") to get user email
        email: str = payload.get("sub")
        if email is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate credentials")
        
        # check db for user
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        if user is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    
    return user # should include current token

async def get_user_by_email(email: str, db: AsyncSession):
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none() # fetch 1 scalar value (None if not found, MultipleResultsFound exception if multiples)
    return user

async def add_new_user(user: User, db: AsyncSession):
    # add new user to db
    db.add(user)
    await db.commit()
    # return await get_user_by_email(user.email)
    return

# validate admin user    
async def admin_required(current_user: User = Depends(get_current_user)):
    if current_user.role.lower() != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin privileges required")
    return current_user