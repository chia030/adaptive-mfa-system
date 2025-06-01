from sqlalchemy import Column, String, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
import uuid
import datetime

# base class for declarative class definitions
Base = declarative_base()

# trusted devices stored for MFA skip
class TrustedDevice(Base):
    __tablename__ = "trusted_devices"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False)
    device_id = Column(String, nullable=False)
    user_agent = Column(String, nullable=True)
    ip_address = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.now)
    expires_at = Column(DateTime, nullable=False)

    def __str__(self):
        return f"TrustedDevice(id={self.id}, user_id={self.user_id}, device_id={self.device_id}, user_agent={self.user_agent}, ip_address={self.ip_address}, created_at={self.created_at}, expires_at={self.expires_at})"

# OTP log should be in the Risk DB perhaps, its only purpose is to train the ML model
class OTPLog(Base):
    __tablename__ = "otp_logs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_id = Column(UUID(as_uuid=True), unique=False, nullable=False)
    email = Column(String, nullable=False)
    timestamp = Column(DateTime, default=datetime.datetime.now)
    status = Column(String, default="requested") # requested/sent/failed/verified
    error = Column(String, nullable=True) # log error messages

    def __str__(self):
        return f"OTPLog(id={self.id}, event_id={self.event_id}, email={self.email}, timestamp={self.timestamp}, status={self.status}, error={self.error})"
