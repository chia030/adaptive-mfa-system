from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from shared_lib.config.settings import settings
from auth_service.app.api.auth import router as auth_router

app = FastAPI(title="Auth Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins, # List of allowed (browser) origins
    allow_credentials=True,
    allow_methods=["*"], # Allow all HTTP methods (e.g., GET, POST, PUT)
    allow_headers=["*"], # Allow all headers
)

# ROUTES:
app.include_router(auth_router, prefix="/auth", tags=["AUTH"]) # AUTH
# tags help documentation (Swagger)

@app.get("/")
def root():
    return {"message": "♥ Auth Service running ♥ Check http://127.0.0.1:8000/docs or http://127.0.0.1:8000/redoc for endpoints."}
