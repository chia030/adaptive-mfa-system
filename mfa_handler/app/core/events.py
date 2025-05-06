import pika, json
from datetime import datetime

conn = pika.BlockingConnection(pika.ConnectionParameters('rabbitmq'))
chan = conn.channel()
chan.exchange_declare('mfa_events', 'topic')

# TODO: perhaps another event should be added in case MFA is not required

def publish_mfa_completed(email, success, method):
    payload = json.dumps({
        "email": email,
        "timestamp": datetime. utcnow().isoformat(),
        "was_successful": success,
        "mfa_method": method
    })
    chan.basic_publish(
        exchange='mfa_events',
        routing_key='mfa.completed',
        body=payload
    )
