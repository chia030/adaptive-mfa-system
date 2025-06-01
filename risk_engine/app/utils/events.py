from datetime import datetime
from shared_lib.schemas.events import RiskScored
from shared_lib.infrastructure.broker import RabbitBroker


def publish_risk_scored(data: RiskScored):
    # print(f"RiskScored: {data}")
    data = {**data.model_dump(), "timestamp": datetime.now().isoformat()}
    body = RiskScored(**data).model_dump_json()
    print(f">Publishing Risk Scored Event Message | Body(JSON): {body}")
    body_bytes = body.encode("utf-8")

    # payload = json.dumps(RiskScored(
    #     **evt.dict(), timestamp=datetime.now().isoformat()
    # ))
    RabbitBroker.publish(exchange='risk_events', routing_key='risk.scored', body=body_bytes)
