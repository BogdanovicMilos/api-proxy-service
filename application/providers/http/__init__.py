# -*- coding: utf-8 -*-
"""Shared HTTP for provider adapters.

Internal to the providers package — adapters import from here, the proxy
layer never does.
"""

from application.providers.http.client import HttpClientConfig, RateLimitedHttpClient

__all__ = ["HttpClientConfig", "RateLimitedHttpClient"]
