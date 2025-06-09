from datetime import datetime
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from shared_lib.infrastructure.db import get_mfa_db
from shared_lib.schemas.events import MFACompleted
from shared_lib.schemas.api import RequestMFACheck, RespondMFACheckData, RespondMFACheck, RequestMFAVerify
from app.utils.schemas import MFARequestIn
from app.utils.events import publish_mfa_completed
from app.core.mfa_logic import send_otp, verify_otp, is_trusted, set_trusted

router = APIRouter()
RISK_THRESHOLD = 50 # risk score threshold for MFA trigger
# RISK_THRESHOLD = 0 # we testin

@router.post("/check", response_model=RespondMFACheck)
async def mfa_check(data: RequestMFACheck, db: AsyncSession = Depends(get_mfa_db)):
    mfa_required = True # just in case
    # check trusted devices
    is_trusted_device = await is_trusted(
        db=db, 
        user_id=data.user_id,
        device_id=data.device_id
        )
    # if device is trusted, skip MFA
    if not is_trusted_device and data.risk_score >= RISK_THRESHOLD:
        print(f">Device unknown and risk score >=50. Sending OTP via email to '{data.email}'.")
        mfa_required = True
        email_sent = await send_otp(
            db=db,
            email=data.email,
            event_id=data.event_id,
            device_id=data.device_id)
        if email_sent != "sent":
            raise HTTPException(status_code=500, detail="Failed to send OTP")
    else:
        mfa_required = False

    resp_data = RespondMFACheckData(event_id=data.event_id, mfa_required=mfa_required)
    response = RespondMFACheck(message="MFA check completed.", data=resp_data)
    status_code = 202 if mfa_required else 200

    print(f">Responding to Auth Service: {response}")
    return JSONResponse(
        status_code=status_code,
        content=response.model_dump(mode="json")
    )

@router.post("/request")
async def mfa_request(data: MFARequestIn):
    send_otp(email=data.email)
    return {"message":f"OTP sent to {data.email}"}

@router.post("/verify")
async def mfa_verify(data: RequestMFAVerify, db: AsyncSession = Depends(get_mfa_db)):
    print(f">Checking cache for OTP with email={data.email}.")
    stored = await verify_otp(
        db=db,
        email=data.email,
        otp=data.otp,
        event_id=data.event_id
        ) # check cache
    
    evt = MFACompleted(
        **data.model_dump(),
        timestamp=datetime.now().isoformat(),
        was_successful=False
    )

    if not stored:
        publish_mfa_completed(evt)
        raise HTTPException(status_code=404, detail="OTP not found, could be expired.")
    elif stored["otp"] != data.otp or stored["device_id"] != data.device_id: # or works like and/or in python
        publish_mfa_completed(evt)
        raise HTTPException(status_code=401, detail="Unauthorized: OTP mismatch." if stored["otp"] != data.otp else "Unauthorized: device fingerprint mismatch.")
    elif UUID(stored["event_id"]) != data.event_id:
        print(f">Event ID mismatch: STORED {stored["event_id"]} vs. RECEIVED {data.event_id}")
    
    # else (all matching)
    evt.was_successful = True
    publish_mfa_completed(evt)

    device_saved = await set_trusted(
        db=db,
        user_id=data.user_id,
        device_id=data.device_id,
        user_agent=data.user_agent,
        ip_address=data.ip_address
    ) # save trusted device for a month

    content = {
            "message": "MFA verified successfully.",
            "device_saved": device_saved
        }

    print(f"Responding to Auth Service: 'status_code=200, content={content}'")

    return JSONResponse(
        status_code=200,
        content=content
    )
