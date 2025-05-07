from fastapi import APIRouter, Depends, HTTPException
from mfa_handler.app.utils.schemas import MFARequestIn, MFAVerifyIn
from mfa_handler.app.core.mfa_logic import send_otp, verify_otp

router = APIRouter()

@router.post("/request")
async def mfa_request(data: MFARequestIn):
    # trigger_mfa(evt) already called via event consumer, this is for manual requests
    send_otp(data.email)
    return {"message":f"OTP sent to {data.email}"}

@router.post("/verify")
async def mfa_verify(data: MFAVerifyIn):
    if not verify_otp(data.email, data.code):
        raise HTTPException(401, "Invalid code")
    return {"message":"MFA passed"}
