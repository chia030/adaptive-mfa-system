import threading
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
# from shared_lib.config.settings import settings
from shared_lib.infrastructure.broker import RabbitBroker
from app.api.risk import router as risk_router
from app.api.db import router as risk_db_router
from app.utils.consumer import start_login_consumer

@asynccontextmanager
async def lifespan(app: FastAPI):
    loop = asyncio.get_event_loop()
    # startup code: launch consumer in a background thread (common use, alternative: multiprocessing)
    threading.Thread(target=start_login_consumer, args=(loop,), daemon=True).start()
    yield
    # shutdown: close connections
    RabbitBroker.stop()

app = FastAPI(title="Risk Engine", lifespan=lifespan)

allowed_origins = [
    # "http://localhost:8080",  # Svelte frontend runs on :8080 | should not be accessed from the front-end
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=False, # Risk & MFA decisions don't require cookies in browser
    allow_methods=["POST"],
    allow_headers=["*"]
)

app.include_router(risk_router, prefix="/risk", tags=["risk"])
app.include_router(risk_db_router, tags=["DB"])

@app.get("/")
def root():
    return {"message": "♥ Risk Engine running ♥ Check http://127.0.0.1:8001/docs or http://127.0.0.1:8001/redoc for endpoints."}

@app.get("/health")
async def health():
    return {"status": "ok"}