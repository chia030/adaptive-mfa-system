from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from shared_lib.config.settings import settings
from mfa_handler.app.api.mfa import router as mfa_router

app = FastAPI(title="MFA Handler")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,  # List of allowed (browser) origins
    allow_credentials=True,
    allow_methods=["POST"], # Allow POST only
    allow_headers=["*"], # Allow all headers
)

# ROUTES:
app.include_router(mfa_router, prefix="/mfa", tags=["MFA"]) # MFA

@app.get("/")
def root():
    return {"message": "♥ MFA Handler running ♥ Check http://127.0.0.1:8002/docs or http://127.0.0.1:8002/redoc for endpoints."}
