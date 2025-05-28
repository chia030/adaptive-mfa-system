from shared_lib.schemas.events import LoginAttempted
from shared_lib.infrastructure.broker import RabbitBroker

def publish_login_event(data: LoginAttempted):

    data = {**data.model_dump(), "timestamp": data.timestamp.isoformat()}
    body = LoginAttempted(**data).model_dump_json()
    print(f">Publishing Login Event Message | Body(JSON): {body}")
    body_bytes = body.encode("utf-8")

    RabbitBroker.publish(exchange="auth_events", routing_key="login.attempted", body=body_bytes)
