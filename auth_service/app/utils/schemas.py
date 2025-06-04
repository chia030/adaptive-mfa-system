from pydantic import BaseModel, EmailStr, model_validator
from typing import Optional
from uuid import UUID
from datetime import datetime

# API Models
class RegisterIn(BaseModel):
    email: EmailStr
    password: str

class RegisterOut(BaseModel):
    message: str = "User registered successfully (with SRP)."

class LoginOut(BaseModel):
    message: str = "Logged in successfully."
    mfa_required: bool = False
    access_token: str = "xxxxx.yyyyy.zzzzz"
    token_type: str = "bearer"

class LoginOutMFA(BaseModel):
    message: str = "MFA Required; OTP sent via email. Complete authentication at /auth/verify-otp."
    mfa_required: bool = True

class LogoutOut(BaseModel):
    message: str = "Logged out {email} successfully."

class ChangePasswordIn(BaseModel):
    email: EmailStr
    new_password: str
    confirm_password: str

    @model_validator(mode="after")
    def passwords_match(self):
        if self.new_password != self.confirm_password:
            raise ValueError("Passwords do not match")
        return self

class ChangePasswordOut(BaseModel):
    message: str = "Password changed for {email}."

class MFAVerifyIn(BaseModel):
    email: EmailStr
    device_id: str # device fingerprint (same as in login)
    otp: int

class MFAVerifyOut(BaseModel):
    message: str = "MFA verified successfully."
    access_token: str = "xxxxx.yyyyy.zzzzz"
    token_type: str = "bearer"

class DeleteUserOut(BaseModel):
    message: str = "Deleted {rowcount} user with email: {email}."

class CurrentUserOut(BaseModel):
    email: EmailStr = "email@email.com"
    id: UUID | str = "555e5555-e55e-55e5-e555-555555550000"
    created_at: datetime = datetime.now()

class SRPStartIn(BaseModel):
    email: EmailStr
    A: str

class SRPVerifyIn(BaseModel):
    email: EmailStr
    A: str
    M: str
