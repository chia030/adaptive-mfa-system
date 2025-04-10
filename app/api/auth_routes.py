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
from fastapi import Request
from app.db.models import LoginAttempt
from app.utils.geolocation import get_geolocation
from app.utils.risk import calculate_risk_score
from datetime import datetime
from fastapi import Header

# new APIRouter instance for authentication
router = APIRouter(tags=["AUTH"]) # tags help documentation (Swagger)

# password hashing context using Argon2
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

# get database session
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
async def login_user(
    # API call dependencies
    request: Request,  # request object to access client IP and user agent
    form_data: OAuth2PasswordRequestForm = Depends(), 
    db: AsyncSession = Depends(get_db),
    x_forwarded_for: str = Header(default=None) # for manual testing
):
    # gather login attempt data 
    # ip = request.client.host
    ip = x_forwarded_for or request.client.host # for manual testing
    user_agent = request.headers.get("user-agent")
    geoloc = await get_geolocation(ip)  # geolocation data from ipapi.co
    now = datetime.utcnow()
    risk = await calculate_risk_score(db, form_data.username, ip, user_agent, now, geoloc.get("country_name"), geoloc.get("region"))
    # init success and user
    success = False
    user = None

    # query for user with email (username in OAuth2PasswordRequestForm)
    result = await db.execute(select(User).where(User.email == form_data.username))
    user = result.scalar_one_or_none()  # fetch 1 user or None

    """
    prev:

    if not user or not pwd_context.verify(form_data.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    
    # JWT access token for authenticated user
    token = create_access_token(data={"sub": user.email})
    """

    if user and pwd_context.verify(form_data.password, user.hashed_password):
        success = True
        # JWT access token for authenticated user
        token = create_access_token(data={"sub": user.email})
    else:
        token = None

    # logging the attempt
    login_record = LoginAttempt(
        user_id=user.id if user else None,
        email=form_data.username,
        ip_address=ip,
        user_agent=user_agent,
        country=geoloc.get("country_name"), # country_name = full name | country = country code
        region=geoloc.get("region"),
        city=geoloc.get("city"),
        timestamp=now,
        was_successful=success,
        risk_score=risk,
    )
    db.add(login_record)
    await db.commit() # commits the transaction

    if not success:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    
    # access token (bearer) returned, exp after an hour
    return {"access_token": token, "token_type": "bearer", "risk_score": risk} # should be stored in the client 

@router.get("/current_user")
async def read_current_user(current_user: User = Depends(get_current_user)):
    return {
        "email": current_user.email,
        "id": str(current_user.id),
        "created_at": current_user.created_at
    }
