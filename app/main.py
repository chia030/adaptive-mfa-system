from fastapi import FastAPI
from app.api.auth_routes import router as auth_router

# Run with uvicorn app.main:app --reload
# should it be running with docker-compose?

app = FastAPI()
app.include_router(auth_router)

@app.get("/")
def root():
    return {"message": "Adaptive MFA System API running."}
