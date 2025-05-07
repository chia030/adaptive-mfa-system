from pydantic import BaseModel, EmailStr, field_validator

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
