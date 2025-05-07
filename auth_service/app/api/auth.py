from jose import jwt, JWTError
import srp
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Body, Request, status, Header
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, update
from auth_service.app.db.models import User
from shared_lib.schemas.events import LoginAttempted
from auth_service.app.utils.schemas import RegisterIn, ChangePasswordIn
from shared_lib.utils.security import create_access_token, pwd_context
from shared_lib.config.settings import settings
from shared_lib.infrastructure.db import get_auth_db
from shared_lib.infrastructure.cache import get_auth_redis
from auth_service.app.utils.geolocation import get_geolocation
from auth_service.app.core.auth_logic import create_access_token, get_current_user
from auth_service.app.utils.events import publish_login_event

srp.rfc5054_enable()

# new APIRouter instance for authentication
router = APIRouter()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login")

# redis
redis = get_auth_redis()

# POST /register => register a new user ======================================================================================
@router.post("/register")
async def register(data: RegisterIn, db: AsyncSession = Depends(get_auth_db)):
    # check if user already exists
    result = await db.execute(select(User).where(User.email == data.email))
    user = result.scalar_one_or_none() # fetch 1 scalar value (None if not found, MultipleResultsFound exception if multiples)
    if user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # password hashed using the CryptContext instance
    hashed_password = pwd_context.hash(data.password)

    # SRP salt & verifier
    salt_bytes, verifier_bytes = srp.create_salted_verification_key(data.email, data.password, hash_alg=srp.SHA256, ng_type=srp.NG_2048)

    # add user to DB
    new_user = User(email=data.email, hashed_password=hashed_password, srp_salt=salt_bytes, srp_verifier=verifier_bytes)
    db.add(new_user)
    await db.commit() # commits the transaction

    return {"message":"User registered successfully (with SRP)"}

# POST /login => log in existing user & return token =========================================================================
@router.post("/login")
async def login_user(
    request: Request,  # request object to access client IP and user agent
    form_data: OAuth2PasswordRequestForm = Depends(), # API call dependencies
    db: AsyncSession = Depends(get_auth_db), # API call dependencies
    device_id: str = Body(...), # device ID
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

    # verify password
    if user and pwd_context.verify(form_data.password, user.hashed_password):
        success = True # TODO: make true only when SRP is verified
    
    # SRP Verify [...] TODO: add later

    

    # login attempt data for message to Risk Engine
    login_metadata = LoginAttempted(
        user_id=user.id if user else None,
        email=form_data.username,
        ip_address=ip,
        device_id=device_id,
        user_agent=user_agent,
        country=geoloc.get("country_name"), # country_name = full name | country = country code
        region=geoloc.get("region"),
        city=geoloc.get("city"),
        timestamp=login_attempt_time,
        was_successful=success,
    )

    # publish login event to Risk Engine
    publish_login_event(login_metadata)

    # calculate Risk Score [...] (in Risk Engine Service) =>

    # => check Trusted Device [...] (in MFA-Handler Service) =>
    # => request OTP if Risk Score is high and device is not trusted [...] (in MFA-Handler Service) =>
    # => if(OTP) return "MFA Required: OTP sent via email." then go to /mfa/verify-otp (in MFA-Handler Service)

    # otherwise... (low risk)
    token = create_access_token(data={"sub":user.email})
    return {"message":"Logged in successfully.", "access_token": token, "token_type": "bearer"}

# POST /logout => log out logged in user ======================================================================================
@router.post("/logout")
async def logout_user(token: str = Depends(oauth2_scheme)): # token is blacklisted in Redis at logout
    # decode token to get expiration time
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        exp_timestamp = payload.get("exp")
        if exp_timestamp is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token missing expiration information")
        now_timestamp = datetime.utcnow().timestamp()
        expires_in = exp_timestamp - now_timestamp
        if expires_in <= 0:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Token is already expired")
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    
    # use token itself as key
    blacklist_key = f"bl:{token}" # prefix bl: for blacklist
    await redis.setex(blacklist_key, int(expires_in), "blacklisted") # store blacklisted token in cache

    return {"message":"Logged out successfully."}

# POST /change-password => change password for existing user ===================================================================
@router.post("/change-password")
async def change_user_password(data: ChangePasswordIn, db: AsyncSession = Depends(get_auth_db)): # NOT SECURE as is :)
    # lookup user
    result = await db.execute(select(User).where(User.email == data.email))
    user = result.scalar_one_or_none() # fetch 1 scalar value (None if not found, MultipleResultsFound exception if multiples)
    if not user: # 404 if not found
        raise HTTPException(status_code=404, detail=f"User with {data.email} not found.")
    
    # TODO: validate current user (with get_current_user())

    # password hashed using the CryptContext instance
    hashed_password = pwd_context.hash(data.new_password)

    # generate new salt & verifier
    salt_bytes, verifier_bytes = srp.create_salted_verification_key(data.email, data.new_password, hash_alg=srp.SHA256, ng_type=srp.NG_2048)

    # change password
    statement = (
        update(User)
        .where(User.id == user.id)
        .values(hashed_password=hashed_password, srp_salt=salt_bytes, srp_verifier=verifier_bytes)
    )
    await db.execute(statement)
    await db.commit()

    # publish audit event?

    return {"message":f"Password changed for {data.email}."}

# DELETE /users/{user_email} => delete existing user ==========================================================================
@router.delete("/users/{email}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(email: str, db: AsyncSession = Depends(get_auth_db)): # NOT SECURE as is :)
    # lookup user
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none() # fetch 1 scalar value (None if not found, MultipleResultsFound exception if multiples)
    if not user: # 404 if not found
        raise HTTPException(status_code=404, detail=f"User with {email} not found.")
    
    # TODO: validate current user (with get_current_user())

    # delete user
    await db.execute(delete(User).where(User.email == email))
    await db.commit()
    # return 204
    return

# GET /current-user => return current active user ==============================================================================
@router.get("/current-user")
async def read_current_user(current_user: User = Depends(get_current_user)):
    return {
        "email": current_user.email,
        "id": str(current_user.id),
        "created_at": current_user.created_at
    }
