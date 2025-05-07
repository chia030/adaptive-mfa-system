import threading
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from shared_lib.config.settings import settings
from shared_lib.infrastructure.broker import RabbitBroker
from risk_engine.app.api.risk import router as risk_router
from risk_engine.app.utils.consumer import start_login_consumer

@asynccontextmanager
async def lifespan(app: FastAPI):
    # startup code: launch consumer in a background thread (common use, alternative: multiprocessing)
    threading.Thread(target=start_login_consumer, daemon=True).start()
    yield
    # shutdown: close connections
    RabbitBroker.stop()

app = FastAPI(title="Risk Engine", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=False, # MFA decisions don't require cookies in browser
    allow_methods=["POST"],
    allow_headers=["*"]
)

app.include_router(risk_router, prefix="/risk", tags=["risk"])

@app.get("/")
def root():
    return {"message": "♥ Risk Engine running ♥ Check http://127.0.0.1:8001/docs or http://127.0.0.1:8001/redoc for endpoints."}
