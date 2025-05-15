import os
import httpx
from shared_lib.config.settings import settings

BREVO_API_KEY = settings.email_api_key.get_secret_value()
SENDER_EMAIL = settings.email_sender

TEMPLATE_PATH = os.path.join(os.path.dirname(__file__), "../templates/email_otp.html")

def load_template(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()

async def send_otp_email(to_email: str, otp: str):
    html_content = load_template(TEMPLATE_PATH).replace("{{ otp }}", otp) # replacing with actual OTP

    url = "https://api.brevo.com/v3/smtp/email"
    headers = {
        "accept": "application/json",
        "api-key": BREVO_API_KEY,
        "content-type": "application/json"
    }
    data = {
        "sender": {"name": "Adaptive MFA System", "email": SENDER_EMAIL},
        "to": [{"email": to_email}],
        "subject": "Your MFA OTP Code",
        "htmlContent": html_content # using the template
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=data, headers=headers)
        if response.status_code >= 400:
            raise Exception(f"Failed to send email: {response.text}")