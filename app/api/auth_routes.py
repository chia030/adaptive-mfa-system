from fastapi import APIRouter, Depends, HTTPException, Body, Request, status, Header
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import AsyncSessionLocal
from app.db.models import User, LoginAttempt, TrustedDevice, OTPLog
from passlib.context import CryptContext
from sqlalchemy import select, delete
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from app.core.security import create_access_token, get_current_user, SECRET_KEY, ALGORITHM
from app.utils.geolocation import get_geolocation
from app.utils.risk import calculate_risk_score
from datetime import datetime
from app.utils.otp import generate_otp
from app.core.redis import redis
from app.utils.email import send_otp_email
from sqlalchemy import and_
import jwt
import srp

srp.rfc5054_enable()

# new APIRouter instance for authentication
router = APIRouter(tags=["AUTH"]) # tags help documentation (Swagger)

# password hashing context using Argon2
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login")

RISK_THRESHOLD = 50
# RISK_THRESHOLD = 0 # for testing

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

    # SRP salt & verifier
    salt_bytes, verifier_bytes = srp.create_salted_verification_key(email, password, hash_alg=srp.SHA256, ng_type=srp.NG_2048)
    # salt = salt_bytes.hex() # create string of hex from bytes object
    # verifier = verifier_bytes.hex()
    
    new_user = User(email=email, hashed_password=hashed_password, srp_salt=salt_bytes, srp_verifier=verifier_bytes)
    
    db.add(new_user)
    await db.commit() # commits the transaction
    
    return {"message": "User registered successfully (with SRP)"}

@router.delete("/users/{email}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user_by_email(email: str, db: AsyncSession = Depends(get_db)):
    # lookup user
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none() # fetch 1 scalar value (None if not found, MultipleResultsFound exception if multiples)
    if not user: # 404 if not found
        raise HTTPException(status_code=404, detail=f"User with {email} not found")
    # delete user
    await db.execute(delete(User).where(User.email == email))
    await db.commit()
    # return 204
    return

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
    device_id: str = Body(...), # device ID
    x_forwarded_for: str = Header(default=None) # for manual testing
):
    # gather login attempt data 
    ip = x_forwarded_for or request.client.host # x_forwarded_for for testing (manual headers input)
    user_agent = request.headers.get("user-agent")
    login_attempt_time = datetime.utcnow()
    geoloc = await get_geolocation(ip)  # geolocation data from ipapi.co

    print(f"\n\ndevice id: {device_id}\n\n")

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

            # send OTP via email (maybe comment out during testing)
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

@router.post("/logout")
async def logout(token: str = Depends(oauth2_scheme)):
    # token is blacklisted in Redis at logout

    # decode token to get expiration time
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        exp_timestamp = payload.get("exp")
        if exp_timestamp is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token missing expiration information")
        now_timestamp = datetime.utcnow().timestamp()
        expires_in = exp_timestamp - now_timestamp
        if expires_in <= 0:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Token is already expired")
    except jwt.PyJWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    
    # use token itself as key
    blacklist_key = f"bl:{token}" # prefix bl: for blacklist
    await redis.setex(blacklist_key, int(expires_in), "blacklisted") # store blacklisted token in cache

    return {"message": "Successfully logged out."}

@router.get("/current_user")
async def read_current_user(current_user: User = Depends(get_current_user)):
    return {
        "email": current_user.email,
        "id": str(current_user.id),
        "created_at": current_user.created_at
    }
