from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
import uuid
import datetime

# base class for declarative class definitions
Base = declarative_base()

# trusted devices stored for MFA skip
class TrustedDevice(Base):
    __tablename__ = "trusted_devices"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)  # fk linking to the User table TODO: remove later
    device_id = Column(String, nullable=False)
    user_agent = Column(String, nullable=True)
    ip_address = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)

    user = relationship("User", backref="trusted_devices")  # relationship to User, access to user + reverse access to trusted devices TODO: remove later

# OTP log should be in the Risk DB perhaps, its only purpose is to train the ML model
class OTPLog(Base):
    __tablename__ = "otp_logs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, nullable=False)
    method = Column(String, nullable=False) # email or sms
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    status = Column(String, default="requested") # requested/sent/failed/verified
    error = Column(String, nullable=True) # log error messages
