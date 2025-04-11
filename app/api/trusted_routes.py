from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import AsyncSessionLocal
from app.core.security import get_current_user
from app.db.models import TrustedDevice
from sqlalchemy.future import select
from datetime import datetime
from app.core.redis import redis

router = APIRouter(prefix="/trusted-devices", tags=["Trusted Devices"])

# get database session
#TODO: make this function global and reuse it in all routers
async def get_db():
    async with AsyncSessionLocal() as session:
        yield session

@router.get("/") # must be authenticated to perform this action
async def get_trusted_devices(current_user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(TrustedDevice).where(
            TrustedDevice.user_id == current_user.id,
            TrustedDevice.expires_at > datetime.utcnow() # returns trusted devices (not expired)
        )
    )
    devices = result.scalars().all()
    
    return [
        {
            "id": str(d.id),
            "device_id": d.device_id,
            "ip_address": d.ip_address,
            "user_agent": d.user_agent,
            "expires_at": d.expires_at,
            "created_at": d.created_at
        } for d in devices
    ]

@router.delete("/{device_id}") # must be authenticated to perform this action
async def revoke_trusted_device(device_id: str, current_user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(TrustedDevice).where(
            TrustedDevice.user_id == current_user.id,
            TrustedDevice.device_id == device_id # device could be expired too, it just needs to exist in db
        )
    )
    device = result.scalar_one_or_none()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    
    await db.delete(device)
    await db.commit()

    await redis.delete(f"trusted:{current_user.id}:{device_id}")  # remove from Redis cache if exists

    return {"message": "Device revoked"}
