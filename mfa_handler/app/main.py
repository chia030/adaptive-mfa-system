from fastapi import FastAPI
from mfa_handler.app.api.mfa import router as mfa_router
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# TODO: add more origins (other microservices)
allowed_origins = [
    "http://localhost:8080",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,  # List of allowed origins
    allow_credentials=True,
    allow_methods=["*"],            # Allow all HTTP methods (e.g., GET, POST, PUT)
    allow_headers=["*"],            # Allow all headers
)

# ROUTES:
app.include_router(mfa_router) # MFA

@app.get("/")
def root():
    return {"message": "♥ System running ♥ Check http://127.0.0.1:8000/docs or http://127.0.0.1:8000/redoc for endpoints."}
