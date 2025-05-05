from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

# SQLAlchemy engine
# `echo=True` logs SQL statements
engine = create_async_engine(DATABASE_URL, echo=True)

# sessionmaker factory asynchronous db sessions
# `expire_on_commit=False` objects remain usable after commits
AsyncSessionLocal = sessionmaker(
    engine, expire_on_commit=False, class_=AsyncSession
)

# get database session
async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
