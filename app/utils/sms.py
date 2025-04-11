import os
from twilio.rest import Client
from dotenv import load_dotenv

load_dotenv()

TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER")

client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

async def send_otp_sms(to_number: str, otp: str):
    message = client.messages.create(
        body=f"Your OTP code is: {otp}",
        from_=TWILIO_PHONE_NUMBER,
        to=to_number
    )
    return message.sid
