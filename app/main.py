from fastapi import FastAPI
from app.api.auth_routes import router as auth_router
from app.api.mfa_routes import router as mfa_router
from app.api.trusted_routes import router as trusted_router
from app.api.admin_routes import router as admin_router
from fastapi.middleware.cors import CORSMiddleware

# Run with uvicorn app.main:app --reload
# should it be running with docker-compose?

app = FastAPI()


allowed_origins = [
    "http://localhost:8080",  # Svelte frontend runs on :8080
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,  # List of allowed origins
    allow_credentials=True,
    allow_methods=["*"],            # Allow all HTTP methods (e.g., GET, POST, PUT)
    allow_headers=["*"],            # Allow all headers
)

# ROUTES:
app.include_router(auth_router) # AUTH
app.include_router(mfa_router) # MFA
app.include_router(trusted_router) # TRUSTED DEVICES (list and revocation)
app.include_router(admin_router) # ADMIN (dashboard)


@app.get("/")
def root():
    return {"message": "♥ System running ♥ Check http://127.0.0.1:8000/docs or http://127.0.0.1:8000/redoc for endpoints."}
