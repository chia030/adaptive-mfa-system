# Shared request/response models
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field
from uuid import UUID

class RequestRiskScore(BaseModel):
    event_id: UUID = Field(..., description="Unique ID for idempotency")
    user_id: Optional[str] = Field(None, description="UUID of the user if known/None for unknown usernames")
    email: EmailStr
    ip_address: str
    user_agent: str
    country: Optional[str] = None
    region: Optional[str] = None
    city: Optional[str] = None
    timestamp: datetime
    was_successful: bool

class RespondRiskScoreData(BaseModel):
    event_id: UUID = Field(..., description="Unique ID for idempotency")
    risk_score: int
    persisted: bool = Field(..., description="True if the login attempt was persisted in the DB, False otherwise")

class RespondRiskScore(BaseModel):
    message: str
    data: RespondRiskScoreData

class RequestMFACheck(BaseModel):
    event_id: UUID = Field(..., description="Unique ID for idempotency")
    user_id: str = Field(..., description="UUID of the user")
    email: EmailStr
    device_id: str
    risk_score: int

class RespondMFACheckData(BaseModel):
    event_id: UUID = Field(..., description="Unique ID for idempotency")
    mfa_required: bool = Field(..., description="True if MFA is required, False otherwise")

class RespondMFACheck(BaseModel):
    message: str
    data: RespondMFACheckData

class RequestMFAVerify(BaseModel):
    event_id: UUID = Field(..., description="Unique ID for idempotency")
    user_id: str
    email: EmailStr
    device_id: str
    user_agent: str
    ip_address: str
    otp: str
