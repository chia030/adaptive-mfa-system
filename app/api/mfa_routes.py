from fastapi import APIRouter, Depends, HTTPException, status, Body
from app.core.redis import redis
from app.utils.otp import generate_otp
from app.core.security import create_access_token
from app.db.models import User
from sqlalchemy.future import select
from app.db.database import AsyncSessionLocal
from app.utils.email import send_otp_email
from app.utils.sms import send_otp_sms

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

# not used for now, just for testing
@router.post("/request-otp-sms")
async def request_otp_sms(to_number: str = Body(...)):
    otp = generate_otp()
    await redis.setex(f"otp:{to_number}", OTP_EXPIRE_SECONDS, otp) # store OTP in Redis with exp (cached)

    # print OTP in terminal
    print(f"\nOTP for {to_number}: {otp}\n")

    # send OTP via SMS
    await send_otp_sms(to_number, otp)

    return {"message": "OTP sent (check terminal and phone)"}

@router.post("/verify-otp")
async def verify_otp(email: str = Body(...), otp: str = Body(...)): # Body(...) is just unspecified body
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
        
        # cache MFA flag for user
        await redis.setex(f"mfa_verified:{user.email}", 600, "true") # exp after 10 min
        
        token = create_access_token(data={"sub": user.email, "mfa": True}) # token stores mfa flag
        return {
            "message": "OTP verified successfully",
            "access_token": token,
            "token_type": "bearer"
        }
