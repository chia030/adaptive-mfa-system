import random, string
from datetime import datetime, timedelta
import json
from sqlalchemy import select, and_
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from shared_lib.infrastructure.db import get_mfa_db
from shared_lib.infrastructure.cache import get_mfa_redis
from app.db.models import TrustedDevice, OTPLog
from app.utils.events import publish_mfa_completed
from app.utils.email import send_otp_email

redis = get_mfa_redis()

RISK_THRESHOLD = 50 # risk score threshold for MFA trigger
OTP_EXPIRE_SECONDS = 300 # 5 minutes

def generate_otp():
    return int(''.join(random.choices(string.digits, k=6)))

async def is_trusted(db: AsyncSession, user_id, device_id):
    is_trusted_device = False
    cache_key = f"trusted:{user_id}:{device_id}"
    print(f">Checking trusted devices '{cache_key}'.")
    cached = redis.get(cache_key)
    # if redis.get(cache_key): return True
    if cached == "true":
        print(">Device found in cache.")
        is_trusted_device = True
    else:
        # fall back to db
        trusted = await db.execute(
            select(TrustedDevice).where(
                and_(
                    TrustedDevice.user_id == user_id,
                    TrustedDevice.device_id == device_id,
                    TrustedDevice.expires_at > datetime.utcnow()
                )
            )
        )
        trusted_device = trusted.scalar_one_or_none() # fetch 1 trusted device or None

        # cache result if found
        if trusted_device:
            print(">Device found in DB. Caching...")
            is_trusted_device = True
            seconds_until_exp = int((trusted_device.expires_at - datetime.utcnow()).total_seconds()) # cache only for the remaining time until expiration
            redis.setex(cache_key, seconds_until_exp, "true")
    print(f">Device not trusted.") if not is_trusted_device else print(f">Device trusted OK.")
    return is_trusted_device
   
async def set_trusted(db: AsyncSession, user_id, device_id, user_agent, ip_address):
    # store trusted device in db
    
    trusted_device = TrustedDevice(
        user_id=user_id,
        device_id=device_id,
        user_agent=user_agent,
        ip_address=ip_address,
        expires_at=datetime.utcnow() + timedelta(days=30) # trusted device expires after 30 days
    )
    print(">Storing trusted device in DB. Data:", trusted_device)
    db.add(trusted_device)
    await db.commit()

    # cache trusted device
    cache_key = f"trusted:{user_id}:{device_id}"
    print(f">Caching trusted device '{cache_key}'.")
    redis.setex(cache_key, 60 * 60 * 24 * 30, "true") # exp after 30 days
    return True

async def send_otp(db: AsyncSession, email, event_id = None, device_id = None): # generate and send otp via email
    key = f"otp:{email}"
    otp = generate_otp()
    print(f">Caching otp, event_id and device_id for {email}")
    redis.setex(key, OTP_EXPIRE_SECONDS, json.dumps({
        "otp": otp,
        "event_id": str(event_id),
        "device_id": device_id
    }))
    print(f">OTP for {email} is: {otp}. It expires in 5 minutes.")
    try:
        await send_otp_email(email, str(otp))
        send_status = "sent"
        error_message = None
    except Exception as e:
        send_status = "failed-send"
        error_message = str(e)

    # log OTP request in db
    otp_log = OTPLog(
        event_id=event_id,
        email=email,
        status=send_status,
        error=error_message,
        timestamp=datetime.utcnow()
    )

    print(">Logging OTP request in DB. Data:", otp_log)
    db.add(otp_log)
    await db.commit()

    return send_status
        

async def verify_otp(db: AsyncSession, email, otp, event_id):
    cached = redis.get(f"otp:{email}")
    otp_status = "verified"
    error_message = None

    print(f"cache store:{cached}")
    # print(f"stored otp: {stored.get("otp")}")
    # print(f"stored otp type: {type(stored.get("otp"))}")

    # OTP expired or not in cache
    if not cached:
        print(">OTP not found.")
        otp_status = "not found"
        error_message = "Unable to verify OTP: OTP not found in cache, could be expired"
    else:
        stored = json.loads(cached)
        print(f"stored otp: {stored.get("otp")}")
        print(f"stored otp type: {type(stored.get("otp"))}")
        # wrong OTP
        if stored.get("otp") != otp:
            print(f">OTP for {email} and {event_id=} invalid.")
            otp_status = "invalid"
            error_message = "Unable to verify OTP: OTP is invalid"
    
    # log OTP request in db
    otp_log = OTPLog(
        event_id=event_id,
        email=email,
        status=otp_status,
        error=error_message,
        timestamp=datetime.utcnow()
    )

    print(">Logging OTP request in DB. Data:", otp_log)
    db.add(otp_log)
    await db.commit()

    print(f">Deleting OTP for {email} from cache.")

    # delete OTP
    redis.delete(f"otp:{email}")

    # success = stored and stored == code
    # publish_mfa_completed(email, success, method="otp")
    return stored
