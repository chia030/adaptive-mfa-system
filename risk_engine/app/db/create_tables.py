from shared_lib.infrastructure.db import init_risk_tables
from models import Base
import asyncio

asyncio.run(init_risk_tables(Base))  # init function to create tables
