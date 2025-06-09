from jose import jwt, JWTError
import srp
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Body, Request, status, Header
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import  delete, update
from uuid import UUID

from shared_lib.schemas.events import LoginAttempted, create_event_id
from shared_lib.schemas.api import RespondRiskScore, RequestMFACheck, RespondMFACheck, RequestMFAVerify
from shared_lib.utils.security import create_access_token, pwd_context
from shared_lib.config.settings import settings
from shared_lib.infrastructure.db import get_auth_db
from shared_lib.infrastructure.cache import get_auth_redis
from shared_lib.infrastructure.clients import get_risk_client, get_mfa_client
from app.db.models import User
from app.utils.schemas import RegisterIn, RegisterOut, LoginOut, LoginOutMFA, LogoutOut, ChangePasswordIn, ChangePasswordOut, MFAVerifyIn, MFAVerifyOut, DeleteUserOut, CurrentUserOut
from app.utils.geolocation import get_geolocation
from app.core.auth_logic import get_current_user, get_user_by_email, add_new_user
from app.utils.events import publish_login_event

srp.rfc5054_enable()

# new APIRouter instance for authentication
router = APIRouter()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


# redis
redis = get_auth_redis()

# POST /register => register a new user ======================================================================================
@router.post(
        "/register",
        summary="Create a new user",
        response_model=RegisterOut,
        status_code=201,
        responses={
            201: {"description": "User created successfully"},
            400: {"description": "Email already exists"}
        }
)
async def register(data: RegisterIn, db: AsyncSession = Depends(get_auth_db)):
    # check if user already exists
    print(f">Checking for user {data.email} in database.")
    user = await get_user_by_email(data.email, db)
    if user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    print(">Hashing password...")    
    # password hashed using the CryptContext instance
    hashed_password = pwd_context.hash(data.password)

    print(">Generating SRP salt and verifier for password...") 
    # SRP salt & verifier
    salt_bytes, verifier_bytes = srp.create_salted_verification_key(data.email, data.password, hash_alg=srp.SHA256, ng_type=srp.NG_2048)

    # add user to DB
    new_user = User(email=data.email, hashed_password=hashed_password, srp_salt=salt_bytes, srp_verifier=verifier_bytes)
    # if add_new_user(new_user) is None:
    #     raise HTTPException(status_code=500, detail="Failed to register user")
    print(f">Registering new user: {data.email} with SRP.")
    await add_new_user(new_user, db)

    response = RegisterOut()

    return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content=response.model_dump(mode="json")
        )

# POST /login => log in existing user & return token =========================================================================
@router.post(
        "/login",
        summary="Log in existing user",
        response_model=LoginOut,
        responses={
            202: {
                "description": "Login successful but MFA is required",
                "model": LoginOutMFA
            },
            401: {"description": "Invalid credentials"},
            502: {"description": "Risk Engine or MFA Handler services are not available or threw an error"}
        }
)
async def login_user(
    request: Request,  # request object to access client IP and user agent
    form_data: OAuth2PasswordRequestForm = Depends(), # API call dependencies
    device_id: str = Body(default="dev-xyz"), # device ID collected from client
    x_forwarded_for: str = Header(default=None), # for manual testing with different IPs
    db: AsyncSession = Depends(get_auth_db), # DB session
    risk_client = Depends(get_risk_client), # Risk Engine client session
    mfa_client = Depends(get_mfa_client) # MFA Handler client session
):
    # gather login attempt data 
    ip = x_forwarded_for or request.client.host # x_forwarded_for for testing (manual headers input)
    user_agent = request.headers.get("user-agent")
    login_attempt_time = datetime.now()
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
    
    # call risk engine -> calculate Risk Score
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

    # call MFA Handler -> decide/challenge
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
        response = LoginOutMFA(mfa_required=True)
        return JSONResponse(
            status_code=202,
            content=response.model_dump(mode="json")
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

    response = LoginOut(mfa_required=False, access_token=token)

    return JSONResponse(
        status_code=200,
        content=response.model_dump(mode="json")
    )

# POST /verify_otp => request MFA verification from MFA Handler ===============================================================
@router.post(
        "/verify-otp",
        summary="Verify OTP for user login",
        response_model=MFAVerifyOut,
        responses={
            400: {"description": "Invalid request: no MFA verification was requested for user or OTP expired"},
            401: {"description": "Invalid OTP or different device_id from requesting device"},
            404: {"description": "User not found"},
            502: {"description": "MFA Handler service is not available or threw an error"}
        }
) # REST call to MFA Handler
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

    try:
        verify_evt = RequestMFAVerify(
            event_id=event_id, # event_id would be empty if not found in cache so the request would fail immediately
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
    except:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid request - no existing OTP found for user.")

    if mfa_r.status_code == 401:
        raise HTTPException(401, "Invalid code or different device ID. Please try again using the same device as the requesting device.")
    elif mfa_r.status_code != 200:
        raise HTTPException(502, "MFA Handler error")
    
    mfa_response = mfa_r.json()
    
    print(">Response from MFA Handler:", f"'{mfa_response.get("message")}'", mfa_r.status_code)
    device_saved = mfa_response.get("device_saved", False)  # default to False if not present
    print(f">Trusted device was saved: {device_saved}.")
    token = create_access_token(subject=user.email)
    response = MFAVerifyOut(message=f"MFA verified successfully. User logged in. Device saved: {device_saved}", access_token=token)
    return JSONResponse(
        status_code=200,
        content=response.model_dump(mode="json")
    )

# POST /logout => log out logged in user ======================================================================================
@router.post(
        "/logout",
        summary="Log out user (blacklist a valid JWT token in cache)",
        response_model=LogoutOut,
        responses={
            400: {"description": "Token already expired"},
            401: {"description": "Token missing expiration info or invalid"}
        }
)
async def logout_user(token: str = Depends(oauth2_scheme)): # token is blacklisted in Redis at logout
    # decode token to get expiration time
    print(">Decoding user's JWT token...")
    email = None
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        email = payload.get("sub")
        exp_timestamp = payload.get("exp")
        if exp_timestamp is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token missing expiration information")
        now_timestamp = datetime.now().timestamp()
        expires_in = exp_timestamp - now_timestamp
        if expires_in <= 0:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Token is already expired")
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    
    print(">Token valid; blacklisting in cache...")
    # use token itself as key
    blacklist_key = f"bl:{token}" # prefix bl: for blacklist
    redis.setex(blacklist_key, int(expires_in), "blacklisted") # store blacklisted token in cache
    response = LogoutOut(message=f"Logged out {email} successfully.")
    return JSONResponse(
        status_code=200,
        content=response.model_dump(mode="json")
    )

# POST /change-password => change password for existing user ===================================================================
@router.post(
        "/change-password",
        summary="Change password for user",
        response_model=ChangePasswordOut,
        responses={
            400: {"description": "New Password and Confirm Password do not match"},
            404: {"description": "User email not found"}
        }
)
async def change_user_password(data: ChangePasswordIn, db: AsyncSession = Depends(get_auth_db)): # NOT SECURE as is :)
    # lookup user
    print(f">Checking for user {data.email} in database.")
    user = await get_user_by_email(data.email, db)
    if not user: # 404 if not found
        raise HTTPException(status_code=404, detail=f"User with {data.email} not found.")
    
    # TODO: validate user via OTP first
    
    print(">Hashing password...")    
    # password hashed using the CryptContext instance
    hashed_password = pwd_context.hash(data.new_password)

    print(">Generating SRP salt and verifier for password...") 
    # generate new salt & verifier
    salt_bytes, verifier_bytes = srp.create_salted_verification_key(data.email, data.new_password, hash_alg=srp.SHA256, ng_type=srp.NG_2048)

    print(">Storing new password...")
    # change password
    statement = (
        update(User)
        .where(User.id == user.id)
        .values(hashed_password=hashed_password, srp_salt=salt_bytes, srp_verifier=verifier_bytes)
    )
    await db.execute(statement)
    await db.commit()

    # publish audit event?

    response = ChangePasswordOut(message=f"Password changed for {data.email}.")

    return JSONResponse(
        status_code=200,
        content=response.model_dump(mode="json")
    )

# DELETE /users/{user_email} => delete existing user ==========================================================================
@router.delete(
        "/users/{email}",
        summary="Delete user account",
        response_model=DeleteUserOut,
        responses={
            404: {"description": "User email not found"}
        }
)
async def delete_user(email: str, db: AsyncSession = Depends(get_auth_db), mfa_client = Depends(get_mfa_client)): # NOT SECURE as is :)
    # lookup user
    print(f">Checking for user {email} in database.")
    user = await get_user_by_email(email, db)
    if not user: # 404 if not found
        raise HTTPException(status_code=404, detail=f"User with {email} not found.")
    
    # TODO: validate current user (with get_current_user())

    print(">Deleting user's trusted devices...")
    # delete user trusted devices
    mfa_trusted_r = await mfa_client.delete(
        f"/trusted/{user.id}"
    )
    print(mfa_trusted_r)
    body_mfa_trusted_r = mfa_trusted_r.json()
    print(body_mfa_trusted_r)

    deleted_trusted_devices = int(body_mfa_trusted_r.get("deleted_rows"))

    print(">Deleting user's OTP Logs...")
    # delete user otp logs
    mfa_logs_r = await mfa_client.delete(
        f"/otp-logs/{user.email}"
    )
    print(mfa_logs_r)
    body_mfa_logs_r = mfa_logs_r.json()
    print(body_mfa_logs_r)

    deleted_otp_logs = int(body_mfa_logs_r.get("deleted_rows"))

    # keeping LoginAttempts to train the model
    print(">Deleting user...")
    # delete user
    result = await db.execute(delete(User).where(User.email == email))
    await db.commit()
    
    response = DeleteUserOut(
        message=f"Deleted {result.rowcount} user with email: {email}.",
        deleted_trusted_devices=deleted_trusted_devices,
        deleted_otp_logs=deleted_otp_logs,
        deleted_users=int(result.rowcount)
    )
    return JSONResponse(
        status_code=200,
        content=response.model_dump(mode="json")
    )

# GET /current-user => return current active user ==============================================================================
@router.get(
        "/current-user",
        summary="Get logged in user (from JWT token)",
        response_model=CurrentUserOut,
        responses={
            401: {"description": "Token has been revoked/Credentials invalid/Token Invalid"},
            404: {"description": "User not found in database"}
        }
)
async def read_current_user(current_user: User = Depends(get_current_user)):
    response = CurrentUserOut(email=current_user.email, id=current_user.id, created_at=current_user.created_at)
    return JSONResponse(
        status_code=200,
        content=response.model_dump(mode="json")
    )
