from fastapi import APIRouter, Depends, HTTPException
from shared_lib.config.settings import settings
from shared_lib.schemas.events import RiskScored
from risk_engine.app.core.risk_logic import compute_risk

router = APIRouter()

@router.post("/predict", response_model=float)
async def predict_risk():
    score = compute_risk()
    return score
