from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from shared_lib.infrastructure.db import get_risk_db
from app.db.models import LoginAttempt

router = APIRouter()

@router.get("/login-attempts")
async def get_all_login_attempts(db: AsyncSession = Depends(get_risk_db)):
    result = await db.execute(select(LoginAttempt))
    login_attempts= result.scalars().all()
    payload = jsonable_encoder({
        "message": "Fetched all login attempts successfully.",
        "data": login_attempts
    })
    return JSONResponse(
        status_code=200,
        content=payload
    )
