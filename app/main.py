# from dotenv import load_dotenv
# import os
from fastapi import FastAPI


# load_dotenv()  # This loads variables from .env into the environment

# # Now you can access them like this:
# db_url = os.getenv("DATABASE_URL")
# print("Connecting to:", db_url)


app = FastAPI()

@app.get("/")
def root():
    return {"message": "Adaptive MFA System API running."}

# Run with uvicorn app.main:app --reload
