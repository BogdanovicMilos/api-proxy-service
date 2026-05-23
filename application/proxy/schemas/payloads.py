# -*- coding: utf-8 -*-
"""Per-operation payload models.

Each model accepts camelCase from the wire (via `alias=`) and exposes
snake_case to Python. `extra="forbid"` ensures clients can't smuggle
unknown fields past validation.
"""
from pydantic import BaseModel, ConfigDict, Field


class _AliasedPayload(BaseModel):
    """Base: accepts camelCase from the wire, exposes snake_case to Python."""

    model_config = ConfigDict(extra="forbid")


class ListLeaguesPayload(_AliasedPayload):
    pass


class GetLeagueMatchesPayload(_AliasedPayload):
    league_shortcut: str = Field(..., alias="leagueShortcut", min_length=1)
    season: str = Field(..., min_length=1)


class GetTeamPayload(_AliasedPayload):
    league_shortcut: str = Field(..., alias="leagueShortcut", min_length=1)
    season: str = Field(..., min_length=1)
    team_id: int = Field(..., alias="teamId")


class GetMatchPayload(_AliasedPayload):
    match_id: int = Field(..., alias="matchId")
