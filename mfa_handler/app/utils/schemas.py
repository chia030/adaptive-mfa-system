from typing import Optional
from pydantic import BaseModel, EmailStr

# API Models
class MFARequestIn(BaseModel):
    user_id: Optional[str]
    email: EmailStr

class MFAVerifyIn(BaseModel):
    user_id: Optional[str]
    email: EmailStr
    device_id: str
    code: str
