# === Pydantic event models ===

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field

# events:
# - publish_login_event(data: LoginAttempted)
# - publish_risk_scored(evt, score)
# - publish_mfa_completed(email, success, method)

class LoginAttempted(BaseModel): # published by Auth Service after login attempt (success or failure)
    user_id: Optional[str] = Field(None, description="UUID of the user if known/None for unknown usernames")
    email: EmailStr
    ip_address: str
    device_id: str
    user_agent: str
    country: Optional[str] = None
    region: Optional[str] = None
    city: Optional[str] = None
    timestamp: datetime
    was_successful: bool

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
