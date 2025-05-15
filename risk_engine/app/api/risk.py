from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from shared_lib.config.settings import settings
from shared_lib.schemas.events import RiskScored, LoginAttempted
from shared_lib.schemas.api import RespondRiskScore, RespondRiskScoreData
from shared_lib.infrastructure.db import get_risk_db
from risk_engine.app.core.risk_logic import compute_risk, persist_login_attempt
from risk_engine.app.core.dumb_risk import calculate_risk_score
from risk_engine.app.db.models import LoginAttempt

router = APIRouter()

# @router.post("/predict", response_model=float)
# async def predict_risk():
#     score = compute_risk()
#     return score

@router.post("/predict", response_model=RespondRiskScore)
async def predict_risk(data: LoginAttempted, db: AsyncSession = Depends(get_risk_db)):
    score = await calculate_risk_score(
        db=db,
        email=data.email, 
        ip=data.ip_address, 
        user_agent=data.user_agent, 
        timestamp=data.timestamp, 
        country=data.country, 
        region=data.region
        )
    
    login_attempt = LoginAttempt(
        event_id=data.event_id,
        user_id=data.user_id,
        email=data.email,
        ip_address=data.ip_address,
        user_agent=data.user_agent,
        country=data.country,
        region=data.region,
        city=data.city,
        timestamp=data.timestamp,
        was_successful=data.was_successful,
        risk_score=score,
    )
    persisted = await persist_login_attempt(db, login_attempt)
    
    if score is None:
        raise HTTPException(status_code=500, detail="Risk score calculation failed")
    
    resp_data = RespondRiskScoreData(event_id=data.event_id, risk_score=score, persisted=persisted)
    response = RespondRiskScore(message="Risk Score calculated.", data=resp_data)
    return JSONResponse(
        status_code=200,
        content=response.model_dump(),
    )
