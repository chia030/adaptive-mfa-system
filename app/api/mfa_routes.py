from fastapi import APIRouter, Depends, HTTPException, status, Body
from app.core.redis import redis
from app.utils.otp import generate_otp
from app.core.security import create_access_token
from app.db.models import User
from sqlalchemy.future import select
from app.db.database import AsyncSessionLocal

router = APIRouter(prefix="/mfa", tags=["MFA"]) # tags help documentation (Swagger)

OTP_EXPIRE_SECONDS = 300 # 5 minutes

@router.post("/request-otp")
async def request_otp(email: str = Body(...)):
    otp = generate_otp()
    await redis.setex(f"otp:{email}", OTP_EXPIRE_SECONDS, otp) # store OTP in Redis with exp (cached)

    # just printing OTP for now, instead of sending via email
    print(f"\nOTP for {email}: {otp}\n")

    return {"message": "OTP sent (check terminal)"}

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
        
        token = create_access_token(data={"sub": user.email})
        return {
            "message": "OTP verified successfully",
            "access_token": token,
            "token_type": "bearer"
        }
