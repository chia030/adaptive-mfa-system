from fastapi import APIRouter, Depends, HTTPException, Body
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
from app.utils.otp import generate_otp
from app.core.redis import redis
from app.utils.email import send_otp_email
from app.db.models import TrustedDevice
from sqlalchemy import and_
from app.core.redis import redis
from app.db.models import OTPLog


# new APIRouter instance for authentication
router = APIRouter(tags=["AUTH"]) # tags help documentation (Swagger)

# password hashing context using Argon2
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

# RISK_THRESHOLD = 50
RISK_THRESHOLD = 0 # for testing

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

# simplest login route, used to test authorized routes in Swagger
@router.post("/login")
async def login_user(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    # query for user with email (username in OAuth2PasswordRequestForm)
    result = await db.execute(select(User).where(User.email == form_data.username))
    user = result.scalar_one_or_none()  # fetch 1 user or None

        # init success and token
    success = False
    token = None

    # verify password
    if user and pwd_context.verify(form_data.password, user.hashed_password):
        success = True

    if not success:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    
    token = create_access_token(data={"sub": user.email})
    # access token (bearer) returned, exp after an hour
    return {"access_token": token, "token_type": "bearer"}

# actual login route that should be used in UI
@router.post("/better-login")
async def login_user_better(
    request: Request,  # request object to access client IP and user agent
    form_data: OAuth2PasswordRequestForm = Depends(), # API call dependencies
    db: AsyncSession = Depends(get_db), # API call dependencies
    device_id: str = Body(...), # device ID is manual input for now, won't be after fingerprinting is implemented
    x_forwarded_for: str = Header(default=None) # for manual testing
):
    # gather login attempt data 
    ip = x_forwarded_for or request.client.host # x_forwarded_for for testing (manual headers input)
    user_agent = request.headers.get("user-agent")
    login_attempt_time = datetime.utcnow()
    geoloc = await get_geolocation(ip)  # geolocation data from ipapi.co

    # query for user with email (username in OAuth2PasswordRequestForm)
    result = await db.execute(select(User).where(User.email == form_data.username))
    user = result.scalar_one_or_none()  # fetch 1 user or None
    
    # init success and token
    success = False
    token = None
    is_trusted_device = False

    # verify password
    if user and pwd_context.verify(form_data.password, user.hashed_password):
        success = True

    # check if device is trusted
    cache_key = f"trusted:{user.id}:{device_id}"
    cached = await redis.get(cache_key)
    if cached == "true":
        is_trusted_device = True
    else:
        # fall back to db
        trusted = await db.execute(
            select(TrustedDevice).where(
                and_(
                    TrustedDevice.user_id == user.id,
                    TrustedDevice.device_id == device_id,
                    TrustedDevice.expires_at > datetime.utcnow()
                )
            )
        )
        trusted_device = trusted.scalar_one_or_none() # fetch 1 trusted device or None

        # cache result if found
        if trusted_device:
            is_trusted_device = True
            seconds_until_exp = int((trusted_device.expires_at - datetime.utcnow()).total_seconds()) # cache only for the remaining time until expiration
            await redis.setex(cache_key, seconds_until_exp, "true")
    
    # determine risk score
    risk_score = await calculate_risk_score(
        db, form_data.username, ip, user_agent, login_attempt_time, 
        country=geoloc.get("country_name"), region=geoloc.get("region")
    )

    # logging the attempt
    login_record = LoginAttempt(
        user_id=user.id if user else None,
        email=form_data.username,
        ip_address=ip,
        user_agent=user_agent,
        country=geoloc.get("country_name"), # country_name = full name | country = country code
        region=geoloc.get("region"),
        city=geoloc.get("city"),
        timestamp=login_attempt_time,
        was_successful=success,
        risk_score=risk_score,
    )
    db.add(login_record)
    await db.commit() # commits the transaction

    if not success:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    
    if success:
        # high risk
        if risk_score >= RISK_THRESHOLD and not is_trusted_device:
            # OTP request trigger
            otp = generate_otp()
            await redis.setex(f"otp:{form_data.username}", 300, otp) # store OTP in Redis with exp (cached)

            # print OTP in terminal
            print(f"\nOTP for {form_data.username}: {otp}\n")

            # send OTP via email, commented out for now
            # await send_otp_email(form_data.username, otp)

            try:
                await send_otp_email(form_data.username, otp)
                send_status = "sent"
                error_message = None
            except Exception as e:
                send_status = "failed-send"
                error_message = str(e)

            # log OTP request in db
            otp_log = OTPLog(
                email=form_data.username,
                method="email",
                status=send_status,
                error=error_message,
                timestamp=datetime.utcnow()
            )
            db.add(otp_log)
            await db.commit()

            if send_status != "sent":
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to send OTP")

            return {
                "message": "MFA required. OTP sent (check terminal)",
                "risk_score": risk_score
            }
            # then call /mfa/verify-otp
        else:
            # low risk
            token = create_access_token(data={"sub": user.email})
    # access token (bearer) returned, exp after an hour
    return {"access_token": token, "token_type": "bearer", "risk_score": risk_score} # should be stored in the client 

#TODO: this login route is becoming huge, move some logic elsewhere?

@router.get("/current_user")
async def read_current_user(current_user: User = Depends(get_current_user)):
    return {
        "email": current_user.email,
        "id": str(current_user.id),
        "created_at": current_user.created_at
    }
