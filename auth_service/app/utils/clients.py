import httpx
from shared_lib.config.settings import settings

async_client: httpx.AsyncClient | None = None

def get_http_client() -> httpx.AsyncClient:
    global async_client
    if async_client is None:
        async_client = httpx.AsyncClient(timeout=5.0)
    return async_client

async def get_risk_client():
    # async with httpx.AsyncClient(base_url="http://risk-engine:8001", timeout=10.0) as risk_client:
    async with httpx.AsyncClient(base_url=settings.risk_engine_url, timeout=10.0) as risk_client: 
        yield risk_client

async def get_mfa_client():
    # async with httpx.AsyncClient(base_url="http://mfa-handler:8002", timeout=10.0) as mfa_client:
    async with httpx.AsyncClient(base_url=settings.mfa_handler_url, timeout=10.0) as mfa_client:
        yield mfa_client
