from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field

# API Models
class MFARequestIn(BaseModel):
    user_id: Optional[str]
    email: EmailStr

class MFAVerifyIn(BaseModel):
    user_id: Optional[str]
    email: EmailStr
    device_id: str
    code: str

# EVENT Models
class RiskScored(BaseModel): # published by Risk Engine after computing risk
    user_id: Optional[str]
    email: EmailStr
    device_id: str
    risk_score: float # 0-100 or 0-1 normalized

class MFACompleted(BaseModel): # published by MFA Handler after MFA challenge is completed
    user_id: Optional[str]
    email: EmailStr
    timestamp: datetime
    was_successful: bool
    mfa_method: str # might not be necessary since only email is available
