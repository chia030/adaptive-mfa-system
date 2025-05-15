from sqlalchemy import Column, String, DateTime, Boolean, Integer, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
import uuid
import datetime

# base class for declarative class definitions
Base = declarative_base()

# TODO: remove fk to User table => DB constraints are replaced by eventual consistency and domain events in Database-Per-Service pattern

# LoginAttempt model to record attempts and train the risk scoring sys
class LoginAttempt(Base):
    __tablename__ = "login_attempts"
    event_id = Column(UUID(as_uuid=True), unique=True, primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=True)
    email = Column(String)
    ip_address = Column(String)  # IP address from login attempt
    device_id = Column(String) # device fingerprint
    user_agent = Column(String)  # user browser or device
    country = Column(String, nullable=True) # geolocation data from ipapi.co
    region = Column(String, nullable=True) # geolocation data from ipapi.co
    city = Column(String, nullable=True) # geolocation data from ipapi.co
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    was_successful = Column(Boolean)
    risk_score = Column(Integer, nullable = True)

# RiskModelMetadata model (after implementing ML model)
# [...]
