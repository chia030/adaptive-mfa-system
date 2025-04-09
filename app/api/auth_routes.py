from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import AsyncSessionLocal
from app.db.models import User
from passlib.context import CryptContext
from sqlalchemy.future import select

# new APIRouter instance for authentication
router = APIRouter()

# password hashing context using Argon2
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

# get a database session
async def get_db():
    async with AsyncSessionLocal() as session:
        yield session

# route to register a new user
@router.post("/register")
async def register_user(email: str, password: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none() # fetch 1 scalar value (None if not found, MultipleResultsFound exception if multiples)
    if user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # password is hashed using the CryptContext instance
    hashed_password = pwd_context.hash(password)
    
    new_user = User(email=email, hashed_password=hashed_password)
    
    db.add(new_user)
    await db.commit() # commits the transaction
    
    return {"message": "User registered successfully"}

# TODO: add other exceptions and messages
