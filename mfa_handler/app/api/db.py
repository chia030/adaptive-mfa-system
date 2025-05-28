from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from uuid import UUID

from shared_lib.infrastructure.db import get_mfa_db
from app.db.models import TrustedDevice, OTPLog

router = APIRouter()

@router.get("/trusted")
async def get_all_trusted_devices(db: AsyncSession = Depends(get_mfa_db)):
    result = await db.execute(select(TrustedDevice))
    trusted = result.scalars().all()
    payload = jsonable_encoder({
        "message": "Fetched all trusted devices successfully.",
        "data": trusted
    })
    return JSONResponse(
        status_code=200,
        content=payload
    )

@router.get("/otp-logs")
async def get_all_otp_logs(db: AsyncSession = Depends(get_mfa_db)):
    result = await db.execute(select(OTPLog))
    logs = result.scalars().all()
    payload = jsonable_encoder({
        "message": "Fetched all otp logs successfully.",
        "data": logs
    })
    return JSONResponse(
        status_code=200,
        content=payload
    )

@router.delete("/trusted")
async def delete_trusted_devices(db: AsyncSession = Depends(get_mfa_db)):
    result = await db.execute(delete(TrustedDevice))
    await db.commit()
    print(f"Deleted {result.rowcount} trusted devices.")
    return

@router.delete("/trusted/{id}")
async def delete_users_trusted_devices(id: UUID, db: AsyncSession = Depends(get_mfa_db)):
    result = await db.execute(delete(TrustedDevice).where(TrustedDevice.user_id == id))
    await db.commit()
    return {"message": f"Deleted {result.rowcount} trusted devices for {id}."}
