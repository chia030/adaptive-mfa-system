from fastapi import FastAPI
from app.api.auth_routes import router as auth_router
from app.api.mfa_routes import router as mfa_router
from app.api.trusted_routes import router as trusted_router

# Run with uvicorn app.main:app --reload
# should it be running with docker-compose?

app = FastAPI()

# ROUTES:
app.include_router(auth_router) # AUTH
app.include_router(mfa_router) # MFA
app.include_router(trusted_router) # TRUSTED DEVICES (list and revocation)

@app.get("/")
def root():
    return {"message": "♥ System running ♥ Check http://127.0.0.1:8000/docs or http://127.0.0.1:8000/redoc for endpoints."}
