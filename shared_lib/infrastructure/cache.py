# Redis factory
import redis
from shared_lib.config.settings import settings

# singleton clients for each service

_auth_redis = None
_risk_redis = None
_mfa_redis = None

def get_auth_redis() -> redis.Redis:
    global _auth_redis
    if _auth_redis is None:
        _auth_redis = redis.Redis.from_url(settings.auth_redis_url, decode_responses=True)
    return _auth_redis

def get_risk_redis() -> redis.Redis:
    global _risk_redis
    if _risk_redis is None:
        _risk_redis = redis.Redis.from_url(settings.risk_redis_url, decode_responses=True)
    return _risk_redis

def get_mfa_redis() -> redis.Redis:
    global _mfa_redis
    if _mfa_redis is None:
        _mfa_redis = redis.Redis.from_url(settings.mfa_redis_url, decode_responses=True)
    return _mfa_redis