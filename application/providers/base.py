# -*- coding: utf-8 -*-
"""Provider-agnostic interface for sports data providers.

Each method returns the raw provider response plus metadata (status code,
target URL, latency) so the proxy layer can audit upstream calls without
needing to know provider-specific shapes.
"""
from dataclasses import dataclass
from typing import Any, Protocol


@dataclass
class ProviderResult:
    data: Any
    status_code: int
    target_url: str
    latency_ms: float


class UpstreamError(Exception):
    """Raised when the upstream provider fails after exhausting retries."""

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        target_url: str | None = None,
        attempts: int = 0,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.target_url = target_url
        self.attempts = attempts


class SportsProvider(Protocol):
    """Interface every sports provider adapter must satisfy."""

    name: str

    async def list_leagues(self) -> ProviderResult: ...

    async def get_league_matches(self, league_shortcut: str, season: str) -> ProviderResult: ...

    async def get_team(self, league_shortcut: str, season: str, team_id: int) -> ProviderResult: ...

    async def get_match(self, match_id: int) -> ProviderResult: ...
