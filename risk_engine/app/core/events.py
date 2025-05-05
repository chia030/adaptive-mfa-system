import pika, json
from datetime import datetime
from risk_engine.app.utils.schemas import RiskScored

conn = pika.BlockingConnection(pika.ConnectionParameters('rabbitmq'))
chan = conn.channel()
chan.exchange_declare('risk_events', 'topic')

def publish_risk_scored(evt, score):
    payload = json.dumps(RiskScored(
        **evt.dict(), risk_score=score, timestamp=datetime.utcnow()
    ))
    chan.basic_publish(
        exchange='risk_events',
        routing_key='risk.scored',
        body=payload
    )
