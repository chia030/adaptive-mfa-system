import httpx
from shared_lib.config.settings import settings

async def get_auth_client():
    async with httpx.AsyncClient(base_url=settings.auth_service_url, timeout=10.0) as auth_client: 
        yield auth_client

async def auth_client():
    return httpx.AsyncClient(
        base_url=settings.auth_service_url,
        timeout=10.0
    )

async def get_risk_client():
    async with httpx.AsyncClient(base_url=settings.risk_engine_url, timeout=10.0) as risk_client: 
        yield risk_client

async def risk_client():
    return httpx.AsyncClient(
        base_url=settings.risk_engine_url,
        timeout=10.0
    )

async def get_mfa_client():
    async with httpx.AsyncClient(base_url=settings.mfa_handler_url, timeout=10.0) as mfa_client:
        yield mfa_client

async def mfa_client():
    return httpx.AsyncClient(
        base_url=settings.mfa_handler_url,
        timeout=10.0
    )
