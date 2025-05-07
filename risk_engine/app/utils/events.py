import json
from datetime import datetime
from shared_lib.schemas.events import RiskScored
from shared_lib.infrastructure.broker import RabbitBroker


def publish_risk_scored(evt, score):
    payload = json.dumps(RiskScored(
        **evt.dict(), risk_score=score, timestamp=datetime.utcnow()
    ))
    RabbitBroker.publish(exchange='risk_events', routing_key='risk.scored', body=payload)
