from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

# SQLAlchemy engine with the database URL
# `echo=True` enables logging of SQL statements for debugging
engine = create_async_engine(DATABASE_URL, echo=True)

# sessionmaker factory for creating asynchronous database sessions
# `expire_on_commit=False` ensures objects remain usable after a commit
AsyncSessionLocal = sessionmaker(
    engine, expire_on_commit=False, class_=AsyncSession
)
