import os
from redis.asyncio import Redis
from dotenv import load_dotenv

load_dotenv()

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

# Redis client instance
redis = Redis.from_url(REDIS_URL, decode_responses=True) # responses returned as strings (not bytes)