from jose import JWTError, jwt
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv

load_dotenv()

# secret key loaded from the environment variable
SECRET_KEY = os.getenv("SECRET_KEY", "supersusjwtkey") # fallback secret key in 2nd arg, used if the env variable is not set
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 # default expiration 

def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()  # copy data to avoid modifying the original
    # set expiration time
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})  # add expiration to token payload
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        # returns None if token is invalid or decoding fails
        return None

#TODO: find a better alternative for datetime.utcnow()
