from jose import jwt, JWTError
import srp
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Body, Request, status, Header
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, update
import httpx
# import json
from uuid import UUID

from shared_lib.schemas.events import LoginAttempted, create_event_id
from shared_lib.schemas.api import RespondRiskScore, RequestMFACheck, RespondMFACheck, RequestMFAVerify
from shared_lib.utils.security import create_access_token, pwd_context
from shared_lib.config.settings import settings
from shared_lib.infrastructure.db import get_auth_db
from shared_lib.infrastructure.cache import get_auth_redis
from app.db.models import User
from app.utils.schemas import RegisterIn, ChangePasswordIn, MFAVerifyIn
from app.utils.geolocation import get_geolocation
from app.core.auth_logic import get_current_user, get_user_by_email, add_new_user
from app.utils.events import publish_login_event
from app.utils.clients import get_http_client, get_risk_client, get_mfa_client

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
    user = await get_user_by_email(data.email, db)
    if user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # password hashed using the CryptContext instance
    hashed_password = pwd_context.hash(data.password)

    # SRP salt & verifier
    salt_bytes, verifier_bytes = srp.create_salted_verification_key(data.email, data.password, hash_alg=srp.SHA256, ng_type=srp.NG_2048)

    # add user to DB
    new_user = User(email=data.email, hashed_password=hashed_password, srp_salt=salt_bytes, srp_verifier=verifier_bytes)
    # if add_new_user(new_user) is None:
    #     raise HTTPException(status_code=500, detail="Failed to register user")
    print(f">Registering new user: {data.email} with SRP.")
    print(">New user data:", new_user)
    await add_new_user(new_user, db)

    return {"message":"User registered successfully (with SRP)"}

# POST /login => log in existing user & return token =========================================================================
@router.post("/login")
async def login_user(
    request: Request,  # request object to access client IP and user agent
    form_data: OAuth2PasswordRequestForm = Depends(), # API call dependencies
    device_id: str = Body(...), # device ID collected from client
    x_forwarded_for: str = Header(default=None), # for manual testing
    db: AsyncSession = Depends(get_auth_db), # DB session
    risk_client = Depends(get_risk_client),
    mfa_client = Depends(get_mfa_client)
):
    # gather login attempt data 
    ip = x_forwarded_for or request.client.host # x_forwarded_for for testing (manual headers input)
    user_agent = request.headers.get("user-agent")
    login_attempt_time = datetime.utcnow()
    geoloc: dict = await get_geolocation(ip)  # geolocation data from ipapi.co

    # init event
    event_id: UUID = create_event_id()

    # init success and token
    success = False
    token = None

    print(f">Checking for user {form_data.username} in database.")
    # query for user with email (username in OAuth2PasswordRequestForm)
    user: User | None = await get_user_by_email(form_data.username, db)
    
    print(">User found:", user) if user else print(">User not found.")
    # verify password
    if user and pwd_context.verify(form_data.password, user.hashed_password):
        print(">Password verified.")
        success = True # TODO: make true only when SRP is verified
    
    # SRP Verify [...] TODO: add later

    # login attempt metadata for Risk Engine
    login_evt = LoginAttempted(
        event_id=event_id,
        user_id=user.id if user else None,
        email=form_data.username,
        ip_address=ip,
        user_agent=user_agent,
        country=geoloc.get("country_name"), # country_name = full name | country = country code
        region=geoloc.get("region"),
        city=geoloc.get("city"),
        timestamp=login_attempt_time,
        was_successful=success,
    )

    # user not found or password invalid
    if not success:
        print(">Login failed for user:", form_data.username)
        publish_login_event(login_evt)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials.")
    

    print(">Requesting risk computation from Risk Engine.")
    print(">Sending data:", login_evt)
    
    # call risk engine synchronously -> calculate Risk Score
    risk_r = await risk_client.post(
        "/risk/predict",
        json=login_evt.model_dump(mode="json")
    )

    if risk_r.status_code != 200:
        raise HTTPException(status_code=502, detail="Risk Engine unavailable")

    # parse risk engine response
    risk_response = RespondRiskScore.model_validate_json(risk_r.content)
    print(">Response from Risk Engine:", f"'{risk_response.message}'", risk_r.status_code)
    print(">Response content: ", f"'{risk_response.data}'")

    if risk_response.data.event_id != event_id:
        raise HTTPException(status_code=502, detail="Risk Engine event ID mismatch")
    
    risk_score = risk_response.data.risk_score
    print(f">Risk Score for user {user.email}: {risk_score}") # just checking

    # risk scored data for MFA Handler
    risk_evt = RequestMFACheck(
        event_id=event_id,
        user_id=user.id,
        email=user.email,
        device_id=device_id,
        risk_score=risk_score
    )

    print(">Requesting MFA check from MFA Handler.")
    print(">Sending data:", risk_evt)

    # call MFA Handler synchronously to decide/challenge
    mfa_r = await mfa_client.post(
        "/mfa/check",
        json=risk_evt.model_dump(mode="json")
    )
 
    # publish login event to MQ (for log)
    publish_login_event(login_evt) # just in case

    # => if(MFA) return "MFA Required: OTP sent via email." then go to /auth/verify-otp
    if mfa_r.status_code == 202:
        print(">MFA Required, storing event ID in cache for 5 minutes.")
        # cache event ID
        redis.setex(f"mfa:{user.email}", 300, str(event_id)) # store event ID in cache for 5 minutes
        return JSONResponse(
            status_code=202,
            content={"mfa_required": True, "message": "MFA Required; OTP sent via email. Complete authentication at /auth/verify-otp."}
        )
    elif mfa_r.status_code != 200:
        raise HTTPException(status_code=502, detail="MFA Handler error.")
    
    # parse mfa handler response
    mfa_response = RespondMFACheck.model_validate_json(mfa_r.content)
    print(">Response from MFA Handler:", f"'{mfa_response.message}'", mfa_r.status_code)
    print(">Response content: ", f"'{mfa_response.data}'")
    
    if mfa_response.data.event_id != event_id:
        raise HTTPException(status_code=502, detail="MFA Handler event ID mismatch")
    
    # otherwise... (low risk)
    print(">MFA not required, creating access token for user.")
    token = create_access_token(subject=user.email) # create JWT token

    return {"message":"Logged in successfully.", "access_token": token, "token_type": "bearer"}

# POST /verify_otp => request MFA verification from MFA Handler ===============================================================
@router.post("/verify-otp") # sync call to MFA Handler
async def verify_otp(request: Request, data: MFAVerifyIn, db: AsyncSession = Depends(get_auth_db), mfa_client = Depends(get_mfa_client)):

    print(f">Checking for user {data.email} in database.")
    user: User | None = await get_user_by_email(data.email, db)
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    ip = request.client.host
    user_agent = request.headers.get("user-agent")

    print(">Fetching event ID from cache.")
    # get event ID from cache
    event_id = redis.get(f"mfa:{user.email}")

    verify_evt = RequestMFAVerify(
        event_id=event_id,
        user_id=user.id,
        email=user.email,
        device_id=data.device_id,
        user_agent=user_agent,
        ip_address=ip,
        otp=data.otp
    )
    print(">Requesting MFA verification from MFA Handler.")
    mfa_r = await mfa_client.post(
    "/mfa/verify",
    json=verify_evt.model_dump(mode="json")
    )

    if mfa_r.status_code == 401:
        raise HTTPException(401, "Invalid code or different device ID. Please try again using the same device as the requesting device.")
    elif mfa_r.status_code != 200:
        raise HTTPException(502, "MFA Handler error")
    
    mfa_response = mfa_r.json()
    
    print(">Response from MFA Handler:", f"'{mfa_response.get("message")}'", mfa_r.status_code)
    # device_saved = mfa_r.content["device_saved"] 
    device_saved = mfa_response.get("device_saved", False)  # default to False if not present
    print(f">Trusted device was saved: {device_saved}.")
    token = create_access_token(subject=user.email)
    return JSONResponse(
        status_code=200,
        content={
            "message": f"MFA verified successfully. User logged in. Device saved: {device_saved}",
            "access_token": token,
            "token_type": "bearer"
        }
    )

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
    user = await get_user_by_email(data.email, db)
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
    user = await get_user_by_email(email, db)
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
