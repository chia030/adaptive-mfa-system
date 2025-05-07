from shared_lib.schemas.events import RiskScored
from shared_lib.infrastructure.broker import RabbitBroker
from mfa_handler.app.core.mfa_logic import trigger_mfa

# callback
def handle_risk_scored(chan, method, props, body):
    # deserialize event
    evt = RiskScored.model_validate_json(body)
    # trigger MFA based on risk score
    trigger_mfa(evt) # business logic

"""
Multiple instances of this service could consume from the same queue, each invoking the callback independently, allowing for scaling.
"""
def start_risk_consumer():
    RabbitBroker.consume(
        exchange='risk_events',
        routing_key='risk.scored',
        queue=None, # rabbitMQ generates a unique, exclusive queue
        on_message=handle_risk_scored,
        durable=True,
        auto_ack=True,
        prefetch_count=1
    )

"""
Callback (on_message) is triggered:
- at subscription time => when basic_consume() is called, pika subscribes callback to a queue
- at message arrival => when a new message lands in the queue, pika dispatches message to callback function on the same thread that called start_consuming()
- auto_ack=True => messages are considered processed as soon as the callback returns TODO: perhaps use manual ack to have some messages persist in the queue for longer
"""
