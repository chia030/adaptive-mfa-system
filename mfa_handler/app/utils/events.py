import json
from datetime import datetime
from shared_lib.infrastructure.broker import RabbitBroker
from shared_lib.schemas.events import MFACompleted

# TODO: perhaps another event should be added in case MFA is not required

def publish_mfa_completed(evt, email, success, method):
    payload = json.dumps(MFACompleted(
        **evt.dict(), email=email, timestamp=datetime.utcnow().isoformat(), was_successful=success, mfa_method=method
    ))
    RabbitBroker.publish(exchange='mfa_events', routing_key='mfa.completed', body=payload)
