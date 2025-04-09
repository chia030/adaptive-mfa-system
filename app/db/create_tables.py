from database import engine
from models import Base
import asyncio

async def init():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)  # create all tables in the db

asyncio.run(init())  # init function to create tables
