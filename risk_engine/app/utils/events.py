from datetime import datetime
from shared_lib.schemas.events import RiskScored
from shared_lib.infrastructure.broker import RabbitBroker


def publish_risk_scored(data: RiskScored):
    data = {**data.model_dump(), "timestamp": datetime.utcnow().isoformat()}
    body = data.model_dump_json()

    # payload = json.dumps(RiskScored(
    #     **evt.dict(), timestamp=datetime.utcnow().isoformat()
    # ))
    RabbitBroker.publish(exchange='risk_events', routing_key='risk.scored', body=body)
