# -*- coding: utf-8 -*-
"""Rate-limited, retrying HTTP client shared by all provider adapters.

Adapters construct this with their base URL + tuning knobs, then call
`get(path, params=...)`. The client owns:

- the per-process token bucket (rate limiting),
- the retry loop with exponential backoff + jitter,
- structured `upstream_call` / `upstream_error` audit logging.

Adapters stay thin: they just know provider-specific paths and response
shape.
"""
import asyncio
import time
from dataclasses import dataclass
from typing import Any

import httpx

from application.logging.audit import audit
from application.providers.base import ProviderResult, UpstreamError
from application.providers.http.rate_limit import TokenBucket
from application.providers.http.retry import TRANSIENT_STATUS, compute_backoff


@dataclass(frozen=True)
class HttpClientConfig:
    """Per-provider tuning. Defaults can come from settings or a literal."""

    base_url: str
    timeout_seconds: float
    rate_per_second: float
    burst: int
    max_retries: int
    backoff_base_seconds: float
    backoff_max_seconds: float
    backoff_jitter_seconds: float


class RateLimitedHttpClient:
    def __init__(self, provider_name: str, config: HttpClientConfig) -> None:
        self._provider_name = provider_name
        self._base_url = config.base_url.rstrip("/")
        self._config = config
        self._bucket = TokenBucket(config.rate_per_second, config.burst)
        self._client = httpx.AsyncClient(timeout=config.timeout_seconds)

    async def aclose(self) -> None:
        await self._client.aclose()

    async def get(self, path: str, params: dict[str, Any] | None = None) -> ProviderResult:
        url = f"{self._base_url}{path}"
        attempt = 0
        last_exc: Exception | None = None
        last_status: int | None = None

        while attempt <= self._config.max_retries:
            await self._bucket.acquire()
            started = time.monotonic()
            try:
                resp = await self._client.get(url, params=params)
                latency_ms = (time.monotonic() - started) * 1000.0
                audit(
                    "upstream_call",
                    provider=self._provider_name,
                    target_url=str(resp.request.url),
                    status_code=resp.status_code,
                    latency_ms=round(latency_ms, 2),
                    attempt=attempt + 1,
                )
                if resp.status_code in TRANSIENT_STATUS:
                    last_status = resp.status_code
                    if attempt >= self._config.max_retries:
                        raise UpstreamError(
                            f"Transient upstream status {resp.status_code}",
                            status_code=resp.status_code,
                            target_url=str(resp.request.url),
                            attempts=attempt + 1,
                        )
                else:
                    resp.raise_for_status()
                    return ProviderResult(
                        data=resp.json() if resp.content else None,
                        status_code=resp.status_code,
                        target_url=str(resp.request.url),
                        latency_ms=latency_ms,
                    )
            except (httpx.TimeoutException, httpx.TransportError) as exc:
                latency_ms = (time.monotonic() - started) * 1000.0
                audit(
                    "upstream_error",
                    provider=self._provider_name,
                    target_url=url,
                    error=type(exc).__name__,
                    detail=str(exc),
                    latency_ms=round(latency_ms, 2),
                    attempt=attempt + 1,
                )
                last_exc = exc
                if attempt >= self._config.max_retries:
                    raise UpstreamError(
                        f"Upstream transport error: {exc}",
                        target_url=url,
                        attempts=attempt + 1,
                    ) from exc
            except httpx.HTTPStatusError as exc:
                raise UpstreamError(
                    f"Upstream HTTP error: {exc.response.status_code}",
                    status_code=exc.response.status_code,
                    target_url=str(exc.request.url),
                    attempts=attempt + 1,
                ) from exc

            attempt += 1
            await asyncio.sleep(
                compute_backoff(
                    attempt,
                    base=self._config.backoff_base_seconds,
                    cap=self._config.backoff_max_seconds,
                    jitter=self._config.backoff_jitter_seconds,
                )
            )

        raise UpstreamError(
            "Upstream failed after retries",
            status_code=last_status,
            target_url=url,
            attempts=attempt,
        ) from last_exc
