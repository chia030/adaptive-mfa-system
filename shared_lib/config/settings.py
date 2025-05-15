# === Pydantic BaseSettings for all env vars ===

from pydantic import BaseSettings, PostgresDsn, RedisDsn, Field, SecretStr, AnyHttpUrl

class Settings(BaseSettings):
    # Allowed Origins (CORSMiddleware)
    allowed_origins: list[str] = Field(default_factory=list, env="ALLOWED_ORIGINS")
    
    # RabbitMQ (single URL)
    rabbitmq_url: str = Field("rabbitmq", env="RABBITMQ_URL")

    # JWT
    jwt_secret_key: SecretStr = Field(..., env="JWT_SECRET_KEY")
    jwt_algorithm: str = Field("HS256", env="JWT_ALGORITHM")

    # AUTH SERVICE
    auth_service_url: AnyHttpUrl = Field(..., env="AUTH_SERVICE_URL")

    # auth service DB
    auth_database_url: PostgresDsn = Field(..., env="AUTH_DB_URL")
    auth_database_url_sync: PostgresDsn = Field(..., env="AUTH_DB_URL_SYNC")

    # auth service Redis
    auth_redis_url: RedisDsn = Field(..., env="AUTH_REDIS_URL")

    # RISK ENGINE
    risk_engine_url: AnyHttpUrl = Field(..., env="RISK_ENGINE_URL")

    # risk engine DB
    risk_database_url: PostgresDsn = Field(..., env="RISK_DB_URL")
    risk_database_url_sync: PostgresDsn = Field(..., env="RISK_DB_URL_SYNC")

    # risk engine Redis
    risk_redis_url: RedisDsn = Field(..., env="RISK_REDIS_URL")

    # MFA HANDLER
    mfa_handler_url: AnyHttpUrl = Field(..., env="MFA_HANDLER_URL")

    # MFA handler Database
    mfa_database_url: PostgresDsn = Field(..., env="MFA_DB_URL")
    mfa_database_url_sync: PostgresDsn = Field(..., env="MFA_DB_URL_SYNC")

    # MFA handler Redis
    mfa_redis_url: RedisDsn = Field(..., env="MFA_REDIS_URL")

    # email provider keys
    email_api_key: SecretStr = Field(..., env="EMAIL_API_KEY")
    email_sender: str        = Field(..., env="EMAIL_SENDER")

    model_path: str = Field("/app/models/risk_model.json", env="MODEL_PATH")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False

settings = Settings()
