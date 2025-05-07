import random, string
from shared_lib.infrastructure.cache import get_mfa_redis
from mfa_handler.app.utils.events import publish_mfa_completed

redis = get_mfa_redis()

def generate_otp():
    return ''.join(random.choices(string.digits, k=6))

def is_trusted(email, device_id):
    key = f"trusted:{email}:{device_id}"
    if redis.get(key): return True
    # fallback to DB query, then cache result [...]

def trigger_mfa(evt):
    # TODO: add conditions => only trigger MFA if device is not trusted and risk score is high
    key = f"otp:{evt.email}"
    otp = generate_otp()
    redis.setex(key, 300, otp) # 5 min exp
    # send via email [...]

def send_otp(email): # without conditions, generate and send otp via email
    key = f"otp:{email}"
    otp = generate_otp()
    redis.setex(key, 300, otp) # 5 min exp
    # send via email [...]

def verify_otp(email, code):
    key = f"otp:{email}"
    stored = redis.get(key)
    success = stored and stored.decode() == code
    publish_mfa_completed(email, success, method="otp")
    return success
