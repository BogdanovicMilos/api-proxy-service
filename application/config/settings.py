# -*- coding: utf-8 -*-
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "API Proxy Service"
    env: str = "local"

    # Provider selection
    sports_provider: str = "openliga"

    # OpenLiga config
    openliga_base_url: str = "https://api.openligadb.de"
    openliga_timeout_seconds: float = 10.0

    # Rate limiting (per-process token bucket)
    openliga_rate_limit_per_second: float = 5.0
    openliga_rate_limit_burst: int = 10

    # Exponential backoff
    openliga_max_retries: int = 3
    openliga_backoff_base_seconds: float = 0.2
    openliga_backoff_max_seconds: float = 5.0
    openliga_backoff_jitter_seconds: float = 0.1

    # Logging
    log_body_truncate_chars: int = 512

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
