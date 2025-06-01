from pydantic import BaseModel, EmailStr, model_validator

# API Models
class RegisterIn(BaseModel):
    email: EmailStr
    password: str

class ChangePasswordIn(BaseModel):
    email: EmailStr
    new_password: str
    confirm_password: str

    @model_validator(mode="after")
    def passwords_match(self):
        if self.new_password != self.confirm_password:
            raise ValueError("Passwords do not match")
        return self

class MFAVerifyIn(BaseModel):
    email: EmailStr
    device_id: str # device fingerprint (same as in login)
    otp: int

class SRPStartIn(BaseModel):
    email: EmailStr
    A: str

class SRPVerifyIn(BaseModel):
    email: EmailStr
    A: str
    M: str
