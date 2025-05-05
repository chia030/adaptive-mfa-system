from sqlalchemy import Column, String, DateTime, LargeBinary
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
import uuid
import datetime

# base class for declarative class definitions
Base = declarative_base()

# User model for the database
class User(Base):
    __tablename__ = "users" # special or reserved attribute are wrapped in __
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False) # remove to be replaced with SRP, keeping for now
    srp_salt = Column(LargeBinary, nullable=False)
    srp_verifier = Column(LargeBinary, nullable=False)
    role = Column(String, nullable=False, default="user") # user or admin
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
