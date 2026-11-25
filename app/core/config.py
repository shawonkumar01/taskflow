from enum import StrEnum
from functools import lru_cache
from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(StrEnum):
    DEVELOPMENT = "development"
    TEST = "test"
    PRODUCTION = "production"


class Settings(BaseSettings):
    """Application settings, loaded from environment variables / .env."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    environment: Environment = Environment.DEVELOPMENT
    database_url: str
    secret_key: str = Field(min_length=32)  # no default: app refuses to start without it
    access_token_expire_minutes: int = Field(default=15, gt=0)
    refresh_token_expire_days: int = Field(default=7, gt=0)

    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    max_request_body_bytes: int = Field(default=1_048_576, gt=0)  # 1 MiB

    # Comma-separated list of allowed browser origins. Empty = CORS disabled.
    cors_origins: str = ""

    rate_limit_enabled: bool = True
    rate_limit_auth: str = "10/minute"
    rate_limit_default: str = "120/minute"
    # Use a shared store (e.g. redis://...) when running more than one process.
    rate_limit_storage_uri: str = "memory://"

    @property
    def is_production(self) -> bool:
        return self.environment == Environment.PRODUCTION

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @model_validator(mode="after")
    def reject_wildcard_cors(self) -> "Settings":
        if "*" in self.cors_origin_list:
            raise ValueError("CORS_ORIGINS must list explicit origins, not '*'.")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
