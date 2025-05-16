from shared_lib.infrastructure.broker import RabbitBroker
from shared_lib.schemas.events import MFACompleted

# TODO: perhaps another event should be added for MFA requests before completion

def publish_mfa_completed(data: MFACompleted):

    data = {**data.model_dump()}
    body = data.model_dump_json()

    # payload = json.dumps(MFACompleted(
    #     **evt.dict(), email=email, timestamp=datetime.utcnow().isoformat(), was_successful=success
    # ))
    RabbitBroker.publish(exchange='mfa_events', routing_key='mfa.completed', body=body)
