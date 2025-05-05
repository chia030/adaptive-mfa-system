import pika
from sqlalchemy.ext.asyncio import AsyncSession
from risk_engine.app.db.db import get_db
from risk_engine.app.utils.schemas import LoginAttempted
from risk_engine.app.risk import compute_risk
from risk_engine.app.core.events import publish_risk_scored

def callback(chan, method, properties, body):
    evt = LoginAttempted.model_validate_json(body)
    db: AsyncSession = get_db()

    # persist attempt
    db.add(evt.to_orm())
    db.commit()

    # compute risk
    score = compute_risk(evt)

    # publish scored event
    publish_risk_scored(evt, score)

def start_consuming():
    conn = pika.BlockingConnection(pika.ConnectionParameters('rabbitmq'))
    chan = conn.channel()
    chan.exchange_declare('auth_events', 'topic')
    q = chan.queue_declare(queue='', exclusive=True).method.queue
    chan.queue_bind(exchange='auth_events', queue=q, routing_key='login.attempted')
    chan.basic_consume(queue=q, on_message_callback=callback, auto_ack=True)
    chan.start_consuming()
