from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from shared_lib.schemas.events import LoginAttempted
from shared_lib.infrastructure.db import get_risk_db
from app.db.models import LoginAttempt

# dumb scoring model
async def calculate_risk_score(
        db: AsyncSession,
        evt: LoginAttempted
) -> int:
    print(f">Calculating risk score for evt: '{evt.event_id}'.")

    score = 0

    """
    TODO: 'was_successful', based on this logic, should really only be set to true once the whole login process is 
          completed, in case the password is hacked.
    """

    # IP risk
    ip_results = await db.execute(
        select(LoginAttempt).where(LoginAttempt.email == evt.email, LoginAttempt.ip_address == evt.ip_address, LoginAttempt.was_successful == True)
    )
    if not ip_results.scalars().first(): # scalars returns the first column value (id) and first() returns the first row only
        score += 30 # new IP

    
    # time risk
    if evt.timestamp.hour < 5 or evt.timestamp.hour > 23:
        score += 20 # odd hours

    
    # device risk
    device_results = await db.execute(
        select(LoginAttempt).where(LoginAttempt.email == evt.email, LoginAttempt.user_agent == evt.user_agent, LoginAttempt.was_successful == True)
    )
    if not device_results.scalars().first(): # as before, check if any results
        score += 20 # new device

    
    # geolocation risk
    if evt.country:
        country_results = await db.execute(
            select(LoginAttempt).where(LoginAttempt.email == evt.email, LoginAttempt.country == evt.country, LoginAttempt.was_successful == True)
        )
        if not country_results.scalars().first():
            score += 15 # new country

    if evt.region:
        region_results = await db.execute(
            select(LoginAttempt).where(LoginAttempt.email == evt.email, LoginAttempt.region == evt.region, LoginAttempt.was_successful == True)
        )
        if not region_results.scalars().first():
            score += 10 # new region

    return min(score, 100) # cap at 100
