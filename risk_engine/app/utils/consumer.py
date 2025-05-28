import asyncio
# from sqlalchemy.ext.asyncio import AsyncSession
# from shared_lib.infrastructure.db import get_risk_db
from shared_lib.infrastructure.db import RiskSessionLocal
from shared_lib.schemas.events import LoginAttempted, RiskScored
from shared_lib.infrastructure.broker import RabbitBroker
from app.db.models import LoginAttempt
from app.core.risk_logic import persist_login_attempt
from app.core.dumb_risk import calculate_risk_score
from app.utils.events import publish_risk_scored
import traceback

# callback
async def handle_login_attempted(chan, method, props, body):

    print(">Received Login Evt Message:", body)

    json_str = body.decode("utf-8") # not needed me thinks
    evt = LoginAttempted.model_validate_json(json_str)

    # db = get_risk_db()
    try:
        async with RiskSessionLocal() as db:
            # compute risk
            # score = compute_risk(evt) # TODO: fix ML model first
            score = await calculate_risk_score(db=db, evt=evt)
            # persist login event
            event_logged, login_attempt = await persist_login_attempt(db=db, evt=evt, score=score)
            risk_scored = RiskScored.from_orm(login_attempt)
            # print(f"RiskScored: {risk_scored}")
            # publish scored event
            publish_risk_scored(data=risk_scored)
    except Exception as e:
        traceback.print_exc()
        traceback.print_stack()

def start_login_consumer(loop):
    def on_message(chan, method, props, body):
        # schedule coroutine on loop from any thread
        # asyncio.run_coroutine_threadsafe(
        #     handle_login_attempted(chan, method, props, body),
        #     loop
        # )
        loop.call_soon_threadsafe(
            lambda: asyncio.create_task(handle_login_attempted(chan, method, props, body))
        )
    RabbitBroker.consume(
        exchange='auth_events',
        routing_key='login.attempted',
        queue=None, # rabbitMQ generates a unique, exclusive queue
        # queue='risk_engine_login_attempts', # specific queue for this consumer instead
        on_message=on_message,
        durable=True,
        auto_ack=True,
        prefetch_count=1
    )
