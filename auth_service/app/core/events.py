"""
LoginAttempted Schema:
{
  "user_id": Optional[str] = Field(None, description="UUID of the user if known/None for unknown usernames")
  "email": EmailStr
  "ip_address": str
  "user_agent": str
  "country": Optional[str] = None
  "region": Optional[str] = None
  "city": Optional[str] = None
  "timestamp": datetime
  "was_successful": bool
}
"""
import pika, json
# from datetime import datetime
from auth_service.app.utils.schemas import LoginAttempted

conn = pika.BlockingConnection(pika.ConnectionParameters("rabbitmq"))
chan = conn.channel()
chan.exchange_declare(exchange="auth_events", exchange_type="topic")

def publish_login_event(data: LoginAttempted):
    body = json.dumps({"user_id": data.user_id, "email":data.email, "ip_address":data.ip_address, "user_agent":data.user_agent, "country":data.country, "region":data.region, "city":data.city, "timestamp":data.timestamp.isoformat(), "success":data.was_successful})
    chan.basic_publish(exchange="auth_events", routing_key="login.attempted", body=body)
