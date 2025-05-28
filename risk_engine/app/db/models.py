from sqlalchemy import Column, String, DateTime, Boolean, Integer, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
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

    def __str__(self):
        return f"LoginAttempt(event_id={self.event_id}, user_id={self.user_id}, email={self.email}, ip_address={self.ip_address}, device_id={self.device_id}, user_agent={self.user_agent}, country={self.country}, region={self.region}, city={self.city}, timestamp={self.timestamp}, was_successful={self.was_successful}, risk_score={self.risk_score})"

# RiskModelMetadata model (after implementing ML model)
# [...]
