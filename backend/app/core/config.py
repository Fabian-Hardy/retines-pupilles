from functools import lru_cache

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment / .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # --- Application ---
    APP_ENV: str = "development"
    APP_VERSION: str = "0.1.0"
    APP_DOMAIN: str = "localhost"
    APP_SECRET_KEY: str = Field(default=..., min_length=32)
    JWT_SECRET_KEY: str = Field(default=..., min_length=32)
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=15, ge=1)
    LOG_LEVEL: str = "INFO"

    # --- Database ---
    # DATABASE_URL is the canonical field. If absent it is assembled from DB_*.
    DATABASE_URL: str = ""
    DB_HOST: str = "postgresql"
    DB_PORT: int = 5432
    DB_NAME: str = "retines_db"
    DB_USER: str = "retines"
    DB_PASS: str = ""

    # --- Redis ---
    REDIS_URL: str = "redis://redis:6379"
    REDIS_HOST: str = "redis"
    REDIS_PORT: int = 6379

    @model_validator(mode="after")
    def _assemble_urls(self) -> "Settings":
        if not self.DATABASE_URL:
            self.DATABASE_URL = (
                f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASS}"
                f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
            )
        return self

    @property
    def cors_origins(self) -> list[str]:
        if self.APP_DOMAIN == "localhost":
            return [
                "http://localhost",
                "http://localhost:5173",
                "http://localhost:3000",
            ]
        return [f"https://{self.APP_DOMAIN}"]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings: Settings = get_settings()
