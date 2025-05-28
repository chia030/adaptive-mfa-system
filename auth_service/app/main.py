import threading
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
# from shared_lib.config.settings import settings
# from shared_lib.infrastructure.broker import RabbitBroker
from app.api.auth import router as auth_router
# from auth_service.app.utils.consumer import start_mfa_consumer

# @asynccontextmanager
# async def lifespan(app: FastAPI):
#     # startup code: launch consumer in a background thread (common use, alternative: multiprocessing)
#     threading.Thread(target=start_mfa_consumer, daemon=True).start()
#     yield
#     # shutdown: close connections
#     RabbitBroker.stop()

# app = FastAPI(title="Auth Service", lifespan=lifespan)
app = FastAPI(title="Auth Service")

allowed_origins = [
    "http://localhost:8080",  # Svelte frontend runs on :8080
]

app.add_middleware(
    CORSMiddleware,
    # allow_origins=settings.allowed_origins, # List of allowed (browser) origins
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"], # Allow all HTTP methods (e.g., GET, POST, PUT, DELETE, etc.)
    allow_headers=["*"], # Allow all headers
)

# ROUTES:
app.include_router(auth_router, prefix="/auth", tags=["AUTH"]) # AUTH
# tags help documentation (Swagger)

@app.get("/")
def root(): 
    return {"message": "♥ Auth Service running ♥ Check http://127.0.0.1:8000/docs or http://127.0.0.1:8000/redoc for endpoints."}
