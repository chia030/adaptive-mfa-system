from fastapi import FastAPI

app = FastAPI()

# allowed_origins = [...]

# CORS middleware [...]

@app.get("/")
def root():
    return {"message": "♥ System running ♥ Check http://127.0.0.1:8000/docs or http://127.0.0.1:8000/redoc for endpoints."}
