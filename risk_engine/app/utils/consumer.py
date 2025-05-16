from sqlalchemy.ext.asyncio import AsyncSession
from shared_lib.infrastructure.db import get_risk_db
from shared_lib.schemas.events import LoginAttempted
from shared_lib.infrastructure.broker import RabbitBroker
from risk_engine.app.core.risk_logic import persist_login_attempt
from risk_engine.app.core.dumb_risk import calculate_risk_score
from risk_engine.app.utils.events import publish_risk_scored

# callback
def handle_login_attempted(chan, method, props, body):
    evt = LoginAttempted.model_validate_json(body)
    db: AsyncSession = get_risk_db()

    # compute risk
    # score = compute_risk(evt) # TODO: fix ML model first
    score = calculate_risk_score(db=db, evt=evt)

    # persist login event
    persist_login_attempt(db=db, evt=evt, score=score)

    # publish scored event
    publish_risk_scored(data=evt)

def start_login_consumer():
    RabbitBroker.consume(
        exchange='auth_events',
        routing_key='login.attempted',
        queue=None, # rabbitMQ generates a unique, exclusive queue
        on_message=handle_login_attempted,
        durable=True,
        auto_ack=True,
        prefetch_count=1
    )
