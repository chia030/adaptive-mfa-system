from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field, field_validator

# API Models
class RegisterIn(BaseModel):
    email: EmailStr
    password: str

class ChangePasswordIn(BaseModel):
    email: EmailStr
    new_password: str
    confirm_password: str

    @field_validator("confirm_password")
    def passwords_match(cls, v, values):
        if "new_password" in values and v != values["new password"]:
            raise ValueError("Passwords do not match")
        return v

class SRPStartIn(BaseModel):
    email: EmailStr
    A: str

class SRPVerifyIn(BaseModel):
    email: EmailStr
    A: str
    M: str

# EVENT Models
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
