import os
import httpx
from dotenv import load_dotenv

load_dotenv()

BREVO_API_KEY = os.getenv("EMAIL_API_KEY")
SENDER_EMAIL = os.getenv("EMAIL_SENDER")

TEMPLATE_PATH = os.path.join(os.path.dirname(__file__), "../templates/email_otp.html")

def load_template(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()

async def send_otp_email(to_email: str, otp: str):
    html_content = load_template(TEMPLATE_PATH).replace("{{ otp }}", otp)

    url = "https://api.brevo.com/v3/smtp/email"
    headers = {
        "accept": "application/json",
        "api-key": BREVO_API_KEY,
        "content-type": "application/json"
    }
    data = {
        "sender": {"name": "Adaptive MFA", "email": SENDER_EMAIL},
        "to": [{"email": to_email}],
        "subject": "Your MFA OTP Code",
        "htmlContent": html_content
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=data, headers=headers)
        if response.status_code >= 400:
            raise Exception(f"Failed to send email: {response.text}")
