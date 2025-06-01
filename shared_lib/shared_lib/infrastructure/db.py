# === DB session maker ===
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from shared_lib.config.settings import settings

# auth service engine & session
auth_engine = create_async_engine(settings.auth_db_url, echo=False, future=True)
AuthSessionLocal = async_sessionmaker(
    bind=auth_engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# risk engine engine & session
risk_engine = create_async_engine(settings.risk_db_url, echo=False, future=True)
RiskSessionLocal = async_sessionmaker(
    bind=risk_engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# MFA handler engine & session
mfa_engine = create_async_engine(settings.mfa_db_url, echo=False, future=True)
MFASessionLocal = async_sessionmaker(
    bind=mfa_engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# dependency helpers for FastAPI
async def get_auth_db():
    async with AuthSessionLocal() as session:
        yield session

async def get_risk_db():
    async with RiskSessionLocal() as session:
        yield session

async def get_mfa_db():
    async with MFASessionLocal() as session:
        yield session

async def init_auth_tables(auth_models: declarative_base):
    async with auth_engine.begin() as conn:
        await conn.run_sync(auth_models.metadata.create_all) # create all tables in the auth db (idempotent, only creates tables if they don't exist)

async def init_risk_tables(risk_models: declarative_base):
    async with risk_engine.begin() as conn:
        await conn.run_sync(risk_models.metadata.create_all)  # create all tables in the risk db (idempotent, only creates tables if they don't exist)
        # await conn.execute(text("CREATE EXTENSION IF NOT EXISTS fuzzystrmatch;"))
        await conn.commit()

async def init_mfa_tables(mfa_models: declarative_base):
    async with mfa_engine.begin() as conn:
        await conn.run_sync(mfa_models.metadata.create_all)  # create all tables in the mfa db (idempotent, only creates tables if they don't exist)
