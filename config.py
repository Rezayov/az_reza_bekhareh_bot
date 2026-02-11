from __future__ import annotations

import os
from functools import lru_cache
from typing import List

from cryptography.fernet import Fernet
from pydantic import BaseSettings, Field, validator


def _default_fernet_key() -> str:
    return Fernet.generate_key().decode("utf-8")


class Settings(BaseSettings):
    bot_token: str = Field("TEST_BOT_TOKEN", env="BOT_TOKEN")
    fernet_key: str = Field(default_factory=_default_fernet_key, env="FERNET_KEY")
    database_url: str = Field("sqlite+aiosqlite:///./az_reza_bekhareh.db", env="DATABASE_URL")
    reserve_ttl_minutes: int = Field(15, env="RESERVE_TTL_MINUTES")
    admin_tg_ids: List[int] = Field(default_factory=list, env="ADMIN_TG_IDS")
    webhook_url: str | None = Field(default=None, env="WEBHOOK_URL")
    log_level: str = Field("INFO", env="LOG_LEVEL")
    reservation_limit_per_user: int = Field(2, env="RESERVATION_LIMIT_PER_USER")
    daily_listing_limit: int = Field(5, env="DAILY_LISTING_LIMIT")
    timezone: str = Field("Asia/Tehran", env="TIMEZONE")
    registration_enabled: bool = Field(True, env="REGISTRATION_ENABLED")

    class Config:
        case_sensitive = False
        env_file = os.getenv("ENV_FILE", ".env")

    @validator("admin_tg_ids", pre=True)
    def parse_admin_ids(cls, value: str | List[int]) -> List[int]:
        if isinstance(value, list):
            return value
        if not value:
            return []
        return [int(part.strip()) for part in value.split(",") if part.strip()]

    @validator("log_level")
    def normalize_level(cls, value: str) -> str:
        return value.upper()


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
