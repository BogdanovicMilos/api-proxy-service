# -*- coding: utf-8 -*-
"""OpenLiga adapter.

All OpenLiga-specific URLs and parameter shapes live here. Rate limiting
and retries are delegated to RateLimitedHttpClient.
"""
from application.providers.base import ProviderResult, SportsProvider
from application.providers.http import RateLimitedHttpClient
from application.providers.openliga.config import openliga_http_config


class OpenLigaProvider(SportsProvider):
    name = "openliga"

    def __init__(self, client: RateLimitedHttpClient | None = None) -> None:
        self._client = client or RateLimitedHttpClient(self.name, openliga_http_config())

    async def aclose(self) -> None:
        await self._client.aclose()

    async def list_leagues(self) -> ProviderResult:
        return await self._client.get("/getavailableleagues")

    async def get_league_matches(self, league_shortcut: str, season: str) -> ProviderResult:
        return await self._client.get(f"/getmatchdata/{league_shortcut}/{season}")

    async def get_team(self, league_shortcut: str, season: str, team_id: int) -> ProviderResult:
        # OpenLiga has no direct /team/{id} endpoint, so we fetch the
        # league's team roster and pick the requested team. The mapper
        # normalizes the chosen entry; if absent, downstream returns null.
        result = await self._client.get(f"/getavailableteams/{league_shortcut}/{season}")
        teams = result.data if isinstance(result.data, list) else []
        match = next((t for t in teams if t.get("teamId") == team_id), None)
        return ProviderResult(
            data=match,
            status_code=result.status_code,
            target_url=result.target_url,
            latency_ms=result.latency_ms,
        )

    async def get_match(self, match_id: int) -> ProviderResult:
        return await self._client.get(f"/getmatchdata/{match_id}")
