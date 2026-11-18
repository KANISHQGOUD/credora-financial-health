from functools import lru_cache

from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Credora API"
    api_v1_prefix: str = "/api/v1"
    database_url: str = "postgresql+psycopg://credora:credora@localhost:5432/credora"
    jwt_secret_key: SecretStr
    jwt_access_token_expire_minutes: int = 30
    cors_origins: str = "http://localhost:5173"
    # Enables the shared read-only demo accounts and seeds them on startup.
    demo_mode: bool = False
    # Sign-up, sign-in and demo requests allowed per client IP (slowapi syntax).
    # Kept generous because a class or office shares one public IP.
    rate_limit_enabled: bool = True
    auth_rate_limit: str = "30/minute"
    # Sign-in attempts allowed per client IP and email address together.
    login_account_rate_limit: str = "5/minute"
    # Interactive API docs at /docs; turn off for public deployments.
    docs_enabled: bool = True

    @field_validator("jwt_secret_key")
    @classmethod
    def secret_long_enough(cls, value: SecretStr) -> SecretStr:
        if len(value.get_secret_value().encode()) < 32:
            raise ValueError("JWT_SECRET_KEY must be at least 32 bytes")
        return value

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
