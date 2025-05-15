from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from shared_lib.infrastructure.db import get_risk_db
from risk_engine.app.db.models import LoginAttempt

model = '' # could use XGBRegressor for now? 

def compute_risk(evt):
    features = evt.to_features_vector()
    return float(model.predict([features])[0])

# TODO: add all the risk logic and save best model in /risk_engine

# save login attempt metadata to db
async def persist_login_attempt(db: AsyncSession, login_attempt: LoginAttempt):
    event_logged = False
    result = await db.execute(select(LoginAttempt).where(
        LoginAttempt.event_id == login_attempt.event_id
    ))
    existing_attempt = result.scalar_one_or_none()

    if existing_attempt:
        print("Event already logged, skipping...")
        return event_logged
    
    try:
        db.add(login_attempt)
        await db.commit()
        event_logged = True
    except Exception as e:
        print ("Failed to log event:", e) 
    return event_logged
