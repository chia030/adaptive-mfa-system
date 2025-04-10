from fastapi import FastAPI
from app.api.auth_routes import router as auth_router
from app.api.mfa_routes import router as mfa_router

# Run with uvicorn app.main:app --reload
# should it be running with docker-compose?

app = FastAPI()
app.include_router(auth_router) # AUTH
app.include_router(mfa_router) # MFA

@app.get("/")
def root():
    return {"message": "♥ System running ♥ Check http://127.0.0.1:8000/docs or http://127.0.0.1:8000/redoc for endpoints."}
