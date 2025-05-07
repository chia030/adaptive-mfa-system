from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from shared_lib.config.settings import settings
from risk_engine.app.api.risk import router as risk_router

app = FastAPI(title="Risk Engine")

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
