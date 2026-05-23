# -*- coding: utf-8 -*-
"""Factory: turn global settings into a typed HttpClientConfig for OpenLiga."""
from application.config.settings import settings
from application.providers.http import HttpClientConfig


def openliga_http_config() -> HttpClientConfig:
    return HttpClientConfig(
        base_url=settings.openliga_base_url,
        timeout_seconds=settings.openliga_timeout_seconds,
        rate_per_second=settings.openliga_rate_limit_per_second,
        burst=settings.openliga_rate_limit_burst,
        max_retries=settings.openliga_max_retries,
        backoff_base_seconds=settings.openliga_backoff_base_seconds,
        backoff_max_seconds=settings.openliga_backoff_max_seconds,
        backoff_jitter_seconds=settings.openliga_backoff_jitter_seconds,
    )
