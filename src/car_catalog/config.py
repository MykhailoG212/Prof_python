"""Environment-backed application settings."""

from functools import lru_cache
from typing import Literal

from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration loaded from environment variables or a .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = Field(
        default="sqlite:///car_catalog.db",
        validation_alias=AliasChoices("DATABASE_URL", "CAR_CATALOG_DATABASE_URL"),
    )
    environment: str = Field(
        default="development",
        validation_alias=AliasChoices("ENVIRONMENT", "CAR_CATALOG_ENVIRONMENT"),
    )
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO",
        validation_alias=AliasChoices("LOG_LEVEL", "CAR_CATALOG_LOG_LEVEL"),
    )
    external_api_url: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "CAR_CATALOG_EXTERNAL_API_URL",
            "EXTERNAL_API_URL",
        ),
    )
    host: str = Field(
        default="0.0.0.0",
        validation_alias=AliasChoices("HOST", "CAR_CATALOG_HOST"),
    )
    port: int = Field(
        default=8000,
        ge=1,
        le=65535,
        validation_alias=AliasChoices("PORT", "CAR_CATALOG_PORT"),
    )

    @field_validator("log_level", mode="before")
    @classmethod
    def normalize_log_level(cls, value: object) -> object:
        if isinstance(value, str):
            return value.upper()
        return value


@lru_cache
def get_settings() -> Settings:
    """Return the process-wide settings instance."""
    return Settings()
