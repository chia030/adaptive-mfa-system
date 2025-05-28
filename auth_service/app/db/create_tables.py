from shared_lib.infrastructure.db import init_auth_tables
from models import Base
import asyncio

asyncio.run(init_auth_tables(Base))  # init function to create tables
