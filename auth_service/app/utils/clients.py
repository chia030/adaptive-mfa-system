import httpx
from shared_lib.config.settings import settings

async_client: httpx.AsyncClient | None = None

def get_http_client() -> httpx.AsyncClient:
    global async_client
    if async_client is None:
        async_client = httpx.AsyncClient(timeout=5.0)
    return async_client
