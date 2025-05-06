import random, string
import redis
from mfa_handler.app.core.events import publish_mfa_completed

redis_client = redis.Redis(host='redis', port=6379)

def generate_otp():
    return ''.join(random.choices(string.digits, k=6))

def is_trusted(email, device_id):
    key = f"trusted:{email}:{device_id}"
    if redis_client.get(key): return True
    # fallback to DB query, then cache result [...]

def trigger_mfa(evt):
    # TODO: add conditions => only trigger MFA if device is not trusted and risk score is high
    key = f"otp:{evt.email}"
    otp = generate_otp()
    redis_client.setex(key, 300, otp) # 5 min exp
    # send via email [...]

def send_otp(email): # without conditions, generate and send otp via email
    key = f"otp:{email}"
    otp = generate_otp()
    redis_client.setex(key, 300, otp) # 5 min exp
    # send via email [...]

def verify_otp(email, code):
    key = f"otp:{email}"
    stored = redis_client.get(key)
    success = stored and stored.decode() == code
    publish_mfa_completed(email, success, method="otp")
    return success
