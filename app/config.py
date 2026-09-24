"""Application configuration for environment-driven settings."""

from __future__ import annotations

import os
from dataclasses import dataclass


def get_env(name: str, default: str | None = None, *, required: bool = False) -> str | None:
    value = os.getenv(name, default)
    if required and (value is None or value == ""):
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


@dataclass(frozen=True)
class Settings:
    """Runtime settings for the cloud pipeline and local development."""

    app_name: str = "ipo_pulse"
    debug: bool = False
    ipo_api_key: str | None = None
    supabase_url: str | None = None
    supabase_key: str | None = None
    email_username: str | None = None
    email_password: str | None = None

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            app_name=get_env("APP_NAME", "ipo_pulse") or "ipo_pulse",
            debug=(get_env("IPO_DEBUG", "false") or "false").lower() == "true",
            ipo_api_key=get_env("IPO_API_KEY"),
            supabase_url=get_env("SUPABASE_URL"),
            supabase_key=get_env("SUPABASE_KEY"),
            email_username=get_env("EMAIL_USERNAME"),
            email_password=get_env("EMAIL_PASSWORD"),
        )


settings = Settings.from_env()
