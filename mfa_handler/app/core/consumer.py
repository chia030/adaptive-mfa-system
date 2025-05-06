import pika
from mfa_handler.app.utils.schemas import RiskScored
from mfa_handler.app.mfa_logic import trigger_mfa

def callback(chan, method, props, body):
    # deserialize event
    evt = RiskScored.model_validate_json(body)
    # trigger MFA based on risk score
    trigger_mfa(evt) # business logic

"""
Multiple instances of this service could consume from the same queue, each invoking the callback independently, allowing for scaling.
"""

# connection and subscription setup
conn = pika.BlockingConnection(pika.ConnectionParameters('rabbitmq'))
chan = conn.channel()
chan.exchange_declare('risk_events', 'topic')
q = chan.queue_declare(queue='', exclusive=True).method.queue
chan.queue_bind(exchange='risk_events', queue=q, routing_key='risk.scored')
chan.basic_consume(queue=q, on_message_callback=callback, auto_ack=True) # basic_consume is single threaded by default
chan.start_consuming()

"""
Callback is triggered:
- at subscription time => when basic_consume() is called, pika subscribes callback to a queue
- at message arrival => when a new message lands in the queue, pika dispatches message to callback function on the same thread that called start_consuming()
- auto_ack=True => messages are considered processed as soon as the callback returns TODO: perhaps use manual ack to have some messages persist in the queue for longer
"""
