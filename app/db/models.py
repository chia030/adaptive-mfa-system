from sqlalchemy import Column, String, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
import uuid
import datetime
from sqlalchemy import ForeignKey, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy import Integer

# base class for declarative class definitions
Base = declarative_base()

# User model for the database
class User(Base):
    __tablename__ = "users" # special or reserved attribute are wrapped in __
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

#TODO: find a better alternative for datetime.utcnow()

#LoginAttempt model to record attempts and train the risk scoring sys
class LoginAttempt(Base):
    __tablename__ = "login_attempts"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)  # fk linking to the User table
    email = Column(String)
    ip_address = Column(String)  # IP address from login attempt
    user_agent = Column(String)  # user browser or device
    country = Column(String, nullable=True) # geolocation data from ipapi.co
    region = Column(String, nullable=True) # geolocation data from ipapi.co
    city = Column(String, nullable=True) # geolocation data from ipapi.co
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    was_successful = Column(Boolean)
    risk_score = Column(Integer, nullable = True)
    user = relationship("User", backref="login_attempts") # relationship to User, access to user + reverse access to login attempts

class TrustedDevice(Base):
    __tablename__ = "trusted_devices"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)  # fk linking to the User table
    device_id = Column(String, nullable=False)
    user_agent = Column(String, nullable=True)
    ip_address = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)

    user = relationship("User", backref="trusted_devices")  # relationship to User, access to user + reverse access to trusted devices
