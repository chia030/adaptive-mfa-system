from shared_lib.infrastructure.broker import RabbitBroker
from shared_lib.schemas.events import MFACompleted

# TODO: perhaps another event should be added for MFA requests before completion

def publish_mfa_completed(data: MFACompleted):

    data = {**data.model_dump()}
    body = MFACompleted(**data).model_dump_json()
    print(f">Publishing MFA Completed Event Message | Body(JSON): {body}")
    body_bytes = body.encode("utf-8")
    
    RabbitBroker.publish(exchange='mfa_events', routing_key='mfa.completed', body=body_bytes)
