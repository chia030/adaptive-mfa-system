from shared_lib.infrastructure.db import init_mfa_tables
from models import Base
import asyncio

asyncio.run(init_mfa_tables(Base))  # init function to create tables
