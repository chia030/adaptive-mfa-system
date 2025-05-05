from fastapi import FastAPI
from auth_service.app.api.auth import router as auth_router
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# TODO: add more origins (other microservices)
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

@app.get("/")
def root():
    return {"message": "♥ System running ♥ Check http://127.0.0.1:8000/docs or http://127.0.0.1:8000/redoc for endpoints."}
