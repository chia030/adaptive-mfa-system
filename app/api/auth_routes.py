from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import AsyncSessionLocal
from app.db.models import User
from passlib.context import CryptContext
from sqlalchemy.future import select
from fastapi.security import OAuth2PasswordRequestForm
from fastapi import status
from app.core.security import create_access_token
from app.core.security import get_current_user
from app.db.models import User

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

@router.post("/login")
async def login_user(form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)): # declare API call dependencies
    # query for user with email (username in OAuth2PasswordRequestForm)
    result = await db.execute(select(User).where(User.email == form_data.username))
    user = result.scalar_one_or_none()  # fetch 1 user or None

    if not user or not pwd_context.verify(form_data.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    
    # JWT access token for authenticated user
    token = create_access_token(data={"sub": user.email})
    
    # access token (bearer) returned, exp after an hour
    return {"access_token": token, "token_type": "bearer"} # should be stored in the client

@router.get("/current_user")
async def read_current_user(current_user: User = Depends(get_current_user)):
    return {
        "email": current_user.email,
        "id": str(current_user.id),
        "created_at": current_user.created_at
    }
