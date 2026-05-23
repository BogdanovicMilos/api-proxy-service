# -*- coding: utf-8 -*-
"""Wire contracts (envelopes) + per-operation payload models.

Re-exports the public symbols so call sites can stay short:

    from application.proxy.schemas import ProxyRequest, GetMatchPayload
"""
from application.proxy.schemas.contracts import ErrorPayload, ProxyRequest, ProxyResponse
from application.proxy.schemas.payloads import (
    GetLeagueMatchesPayload,
    GetMatchPayload,
    GetTeamPayload,
    ListLeaguesPayload,
)

__all__ = [
    "ErrorPayload",
    "GetLeagueMatchesPayload",
    "GetMatchPayload",
    "GetTeamPayload",
    "ListLeaguesPayload",
    "ProxyRequest",
    "ProxyResponse",
]
