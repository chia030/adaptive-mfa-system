from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from shared_lib.config.settings import settings
from shared_lib.schemas.events import RiskScored, LoginAttempted
from shared_lib.schemas.api import RespondRiskScore, RespondRiskScoreData
from shared_lib.infrastructure.db import get_risk_db
from app.core.risk_logic import persist_login_attempt
from app.core.dumb_risk import calculate_risk_score
from app.db.models import LoginAttempt
from app.utils.events import publish_risk_scored

router = APIRouter()

# @router.post("/predict", response_model=float)
# async def predict_risk():
#     score = compute_risk()
#     return score

@router.post("/predict", response_model=RespondRiskScore)
async def predict_risk(data: LoginAttempted, db: AsyncSession = Depends(get_risk_db)):
    score = await calculate_risk_score(
        db=db,
        evt=data
        )
    
    if score is None:
        raise HTTPException(status_code=500, detail="Risk score calculation failed")
    
    print(">Calculated risk score:", score)
    
    event_logged, login_attempt = await persist_login_attempt(db=db, evt=data, score=score)
    
    resp_data = RespondRiskScoreData(event_id=data.event_id, risk_score=score, persisted=event_logged)
    response = RespondRiskScore(message="Risk Score calculated.", data=resp_data)

    evt = RiskScored(
        **data.model_dump(exclude={"timestamp"}),
        risk_score=score,
        timestamp=datetime.utcnow().isoformat(),
    )
    
    # evt.timestamp = datetime.utcnow().isoformat()

    publish_risk_scored(data=evt)

    print(">Responding to Auth Service:", response)

    return JSONResponse(
        status_code=200,
        content=response.model_dump(mode="json")
    )
