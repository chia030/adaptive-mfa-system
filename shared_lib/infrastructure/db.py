# === DB session maker ===
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from shared_lib.config.settings import settings

# auth service engine & session
auth_engine = create_async_engine(settings.auth_database_url, echo=False, future=True)
AuthSessionLocal = async_sessionmaker(
    bind=auth_engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# risk engine engine & session
risk_engine = create_async_engine(settings.risk_database_url, echo=False, future=True)
RiskSessionLocal = async_sessionmaker(
    bind=risk_engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# MFA handler engine & session
mfa_engine = create_async_engine(settings.mfa_database_url, echo=False, future=True)
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
