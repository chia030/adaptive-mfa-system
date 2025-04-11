from fastapi import APIRouter, Depends, HTTPException, status, Body
from app.core.redis import redis
from app.utils.otp import generate_otp
from app.core.security import create_access_token
from app.db.models import User
from sqlalchemy.future import select
from app.db.database import AsyncSessionLocal
from app.utils.email import send_otp_email
from app.db.models import TrustedDevice
from datetime import timedelta, datetime
from fastapi import Request

router = APIRouter(prefix="/mfa", tags=["MFA"]) # tags help documentation (Swagger)

OTP_EXPIRE_SECONDS = 300 # 5 minutes

# not used for now, just for testing
@router.post("/request-otp")
async def request_otp(email: str = Body(...)):
    otp = generate_otp()
    await redis.setex(f"otp:{email}", OTP_EXPIRE_SECONDS, otp) # store OTP in Redis with exp (cached)

    # print OTP in terminal
    print(f"\nOTP for {email}: {otp}\n")

    # send OTP via email
    await send_otp_email(email, otp)

    return {"message": "OTP sent (check terminal and email)"}

@router.post("/verify-otp")
async def verify_otp(
    request: Request, 
    email: str = Body(...), # Body(...) is just unspecified body
    device_id: str = Body(...), # device ID is manual input for now, won't be after fingerprinting is implemented
    otp: str = Body(...)
    ): 
    stored = await redis.get(f"otp:{email}") # check if OTP in cache
    if not stored or stored != otp:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired OTP")
    
    # delete OTP
    await redis.delete(f"otp:{email}")

    # issue JWT token
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        
        expires_at = datetime.utcnow() + timedelta(days=30) # trusted device expires after 30 days
        
        # store trusted device in db (should be prompted in frontend not automatic)
        trusted = TrustedDevice(
            user_id=user.id,
            device_id=device_id,
            user_agent=request.headers.get("user-agent"),
            ip_address=request.client.host,
            expires_at=expires_at
        )
        db.add(trusted)
        await db.commit()
        
        # cache MFA flag for user
        await redis.setex(f"mfa_verified:{user.email}", 600, "true") # exp after 10 min

        # cache trusted device
        await redis.setex(f"trusted:{user.id}:{device_id}", 60 * 60 * 24 * 30, "true") # exp after 30 days
        
        token = create_access_token(data={"sub": user.email, "mfa": True}) # token stores mfa flag
        return {
            "message": "OTP verified successfully",
            "access_token": token,
            "token_type": "bearer"
        }
