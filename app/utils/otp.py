import random

def generate_otp(length: int = 6) -> str:
    # OTP = string of 6 random digits
    return ''.join([str(random.randint(0, 9)) for _ in range(length)])
