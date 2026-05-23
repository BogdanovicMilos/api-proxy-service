# -*- coding: utf-8 -*-
"""Decision mapper: schema-driven routing for the proxy endpoint.

Each operation is described by an `Operation` entry that bundles:
- a Pydantic model for payload validation (from schemas.payloads)
- a `call` coroutine that invokes the provider adapter
- a `normalize` callable that maps the provider's raw response into a
  provider-agnostic shape (from normalizers)

Adding a new operation = adding a new `Operation` entry below.
"""

from dataclasses import dataclass
from typing import Any, Awaitable, Callable

from pydantic import BaseModel, ValidationError

from application.providers.base import ProviderResult, SportsProvider
from application.proxy.errors import PayloadValidationError, UnknownOperationError
from application.proxy.normalizers import (
    normalize_leagues_response,
    normalize_match_response,
    normalize_matches_response,
    normalize_team,
)
from application.proxy.schemas import (
    GetLeagueMatchesPayload,
    GetMatchPayload,
    GetTeamPayload,
    ListLeaguesPayload,
)

CallFn = Callable[[SportsProvider, BaseModel], Awaitable[ProviderResult]]
NormalizeFn = Callable[[Any], Any]


@dataclass(frozen=True)
class Operation:
    name: str
    payload_model: type[BaseModel]
    call: CallFn
    normalize: NormalizeFn


# ------------------------------------------------------------------
# Per-operation call
# ------------------------------------------------------------------


async def _call_list_leagues(provider: SportsProvider, _payload: BaseModel) -> ProviderResult:
    return await provider.list_leagues()


async def _call_get_league_matches(provider: SportsProvider, payload: BaseModel) -> ProviderResult:
    assert isinstance(payload, GetLeagueMatchesPayload)
    return await provider.get_league_matches(payload.league_shortcut, payload.season)


async def _call_get_team(provider: SportsProvider, payload: BaseModel) -> ProviderResult:
    assert isinstance(payload, GetTeamPayload)
    return await provider.get_team(payload.league_shortcut, payload.season, payload.team_id)


async def _call_get_match(provider: SportsProvider, payload: BaseModel) -> ProviderResult:
    assert isinstance(payload, GetMatchPayload)
    return await provider.get_match(payload.match_id)


# ------------------------------------------------------------------
# Registry
# ------------------------------------------------------------------


_OPERATIONS: dict[str, Operation] = {
    "ListLeagues": Operation(
        "ListLeagues",
        ListLeaguesPayload,
        _call_list_leagues,
        normalize_leagues_response,
    ),
    "GetLeagueMatches": Operation(
        "GetLeagueMatches",
        GetLeagueMatchesPayload,
        _call_get_league_matches,
        normalize_matches_response,
    ),
    "GetTeam": Operation(
        "GetTeam",
        GetTeamPayload,
        _call_get_team,
        normalize_team,
    ),
    "GetMatch": Operation(
        "GetMatch",
        GetMatchPayload,
        _call_get_match,
        normalize_match_response,
    ),
}


# ------------------------------------------------------------------
# Public
# ------------------------------------------------------------------


def resolve_operation(operation_type: str) -> Operation:
    operation = _OPERATIONS.get(operation_type)
    if operation is None:
        raise UnknownOperationError(
            f"Unknown operationType '{operation_type}'",
            details=[f"supported: {sorted(_OPERATIONS.keys())}"],
        )
    return operation


def validate_payload(operation: Operation, payload: dict[str, Any]) -> BaseModel:
    try:
        return operation.payload_model.model_validate(payload)
    except ValidationError as exc:
        details = [f"{'.'.join(str(p) for p in err['loc'])}: {err['msg']}" for err in exc.errors()]
        raise PayloadValidationError(
            f"Invalid payload for operation '{operation.name}'",
            details=details,
        ) from exc


def supported_operations() -> list[str]:
    return sorted(_OPERATIONS.keys())
