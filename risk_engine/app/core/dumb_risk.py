from datetime import datetime
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from shared_lib.infrastructure.db import get_risk_db
from risk_engine.app.db.models import LoginAttempt

# dumb scoring model
async def calculate_risk_score(
        db: AsyncSession,
        email: str,
        ip: str,
        user_agent: str,
        timestamp: datetime,
        country: str = None,
        region: str = None
) -> int:
    score = 0

    # IP risk
    ip_results = await db.execute(
        select(LoginAttempt).where(LoginAttempt.email == email, LoginAttempt.ip_address == ip)
    )
    if not ip_results.scalars().first(): # scalars returns the first column value (id) and first() returns the first row only
        score += 30 # new IP

    
    # time risk
    if timestamp.hour < 5 or timestamp.hour > 23:
        score += 20 # odd hours

    
    # device risk
    device_results = await db.execute(
        select(LoginAttempt).where(LoginAttempt.email == email, LoginAttempt.user_agent == user_agent)
    )
    if not device_results.scalars().first(): # as before, check if any results
        score += 20 # new device

    
    # geolocation risk
    if country:
        country_results = await db.execute(
            select(LoginAttempt).where(LoginAttempt.email == email, LoginAttempt.country == country)
        )
        if not country_results.scalars().first():
            score += 15 # new country

    if region:
        region_results = await db.execute(
            select(LoginAttempt).where(LoginAttempt.email == email, LoginAttempt.region == region)
        )
        if not region_results.scalars().first():
            score += 10 # new region

    return min(score, 100) # cap at 100
