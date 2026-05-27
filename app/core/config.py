from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")
    
    PROJECT_NAME: str = "Messenger API"
    VERSION:      str = "2.0.0"
    DESCRIPTION:  str = "A simple messaging API built with FastAPI and SQLModel."
    API_PREFIX:   str = "/api/v1"

    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM:  str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24

    DATABASE_URL: str = "sqlite:///./messenger.db"
    REDIS_URL:    str | None = None

    EMAIL_SMTP_HOST:     str | None = None
    EMAIL_SMTP_PORT:     int = 587
    EMAIL_SMTP_USER:     str | None = None
    EMAIL_SMTP_PASSWORD: str | None = None
    EMAIL_FROM:          str | None = None
    EMAIL_SMTP_USE_SSL:  bool = False
    EMAIL_SMTP_STARTTLS: bool = True


settings = Settings()
