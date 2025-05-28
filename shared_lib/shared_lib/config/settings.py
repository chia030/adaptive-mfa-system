# === Pydantic BaseSettings for all env vars ===

from pydantic import PostgresDsn, RedisDsn, Field, SecretStr, AnyHttpUrl, AmqpDsn
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):

    # Allowed Origins (CORSMiddleware)
    # allowed_origins: list[str] = Field(default_factory=list, env="ALLOWED_ORIGINS")
    
    # RabbitMQ (single URL)
    rabbitmq_url: str = Field(..., env="RABBITMQ_URL")

    # JWT
    jwt_secret_key: str = Field(..., env="JWT_SECRET_KEY")
    jwt_algorithm: str = Field("HS256", env="JWT_ALGORITHM")

    # AUTH SERVICE
    auth_service_url: str = Field(..., env="AUTH_SERVICE_URL")

    # auth service DB
    auth_db_url: str = Field(..., env="AUTH_DB_URL")
    # auth_db_url_sync: PostgresDsn = Field(..., env="AUTH_DB_URL_SYNC")

    # auth service Redis
    auth_redis_url: str = Field(..., env="AUTH_REDIS_URL")

    # RISK ENGINE (url to reach it from other docker containers!)
    risk_engine_url: str = Field(..., env="RISK_ENGINE_URL")

    # risk engine DB
    risk_db_url: str = Field(..., env="RISK_DB_URL")
    # risk_db_url_sync: PostgresDsn = Field(..., env="RISK_DB_URL_SYNC")

    # risk engine Redis
    risk_redis_url: str = Field(..., env="RISK_REDIS_URL")

    # MFA HANDLER
    mfa_handler_url: str = Field(..., env="MFA_HANDLER_URL")

    # MFA handler DB
    mfa_db_url: str = Field(..., env="MFA_DB_URL")
    # mfa_db_url_sync: PostgresDsn = Field(..., env="MFA_DB_URL_SYNC")

    # MFA handler Redis
    mfa_redis_url: str = Field(..., env="MFA_REDIS_URL")

    # email provider keys
    email_api_key: str = Field(..., env="EMAIL_API_KEY")
    email_sender: str        = Field("chiaryilary23@gmail.com", env="EMAIL_SENDER")

    model_config = SettingsConfigDict(
        env_file = "../../.env",
        case_sensitive = False,
        extra="ignore"
    )

    # model_path: str = Field("/app/models/risk_model.json", env="MODEL_PATH")

settings = Settings()
