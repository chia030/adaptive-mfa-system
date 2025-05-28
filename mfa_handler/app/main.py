import threading
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
# from shared_lib.config.settings import settings
from shared_lib.infrastructure.broker import RabbitBroker
from app.api.mfa import router as mfa_router
from app.api.db import router as mfa_db_router
# from mfa_handler.app.utils.consumer import start_risk_consumer

# == CONSUMER
# @asynccontextmanager
# async def lifespan(app: FastAPI):
#     # startup code: launch consumer in a background thread (common use, alternative: multiprocessing)
#     threading.Thread(target=start_risk_consumer, daemon=True).start()
#     yield
#     # shutdown: close connections
#     RabbitBroker.stop()
# app = FastAPI(title="MFA Handler", lifespan=lifespan)
# ==

app = FastAPI(title="MFA Handler")

allowed_origins = [
    "http://localhost:8080",  # Svelte frontend runs on :8080
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,  # List of allowed (browser) origins
    allow_credentials=True,
    # allow_methods=["POST"], # Allow POST only
    allow_methods=["*"],
    allow_headers=["*"], # Allow all headers
)

# ROUTES:
app.include_router(mfa_router, prefix="/mfa", tags=["MFA"]) # MFA
app.include_router(mfa_db_router, tags=["DB"])

@app.get("/")
def root():
    return {"message": "♥ MFA Handler running ♥ Check http://127.0.0.1:8002/docs or http://127.0.0.1:8002/redoc for endpoints."}
