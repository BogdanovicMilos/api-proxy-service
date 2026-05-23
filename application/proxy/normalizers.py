# -*- coding: utf-8 -*-
"""Pure functions mapping provider-raw shapes into our public shape.

Keys returned here are camelCase because they're emitted to JSON clients
directly. No business logic, no I/O — easy to unit-test in isolation.
"""
from typing import Any


def normalize_league(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": item.get("leagueId"),
        "name": item.get("leagueName"),
        "shortcut": item.get("leagueShortcut"),
        "season": item.get("leagueSeason"),
        "sport": (item.get("sport") or {}).get("sportName"),
    }


def normalize_team(item: dict[str, Any] | None) -> dict[str, Any] | None:
    if item is None:
        return None
    return {
        "id": item.get("teamId"),
        "name": item.get("teamName"),
        "shortName": item.get("shortName"),
        "iconUrl": item.get("teamIconUrl"),
    }


def normalize_goal(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": item.get("goalId"),
        "scoreTeam1": item.get("scoreTeam1"),
        "scoreTeam2": item.get("scoreTeam2"),
        "minute": item.get("matchMinute"),
        "scorer": item.get("goalGetterName"),
        "isPenalty": item.get("isPenalty"),
        "isOwnGoal": item.get("isOwnGoal"),
        "isOvertime": item.get("isOvertime"),
    }


def normalize_match(item: dict[str, Any]) -> dict[str, Any]:
    results = item.get("matchResults") or []
    final = next(
        (r for r in results if r.get("resultTypeID") == 2),
        results[0] if results else None,
    )
    return {
        "id": item.get("matchID"),
        "kickoff": item.get("matchDateTime"),
        "isFinished": item.get("matchIsFinished"),
        "leagueId": item.get("leagueId"),
        "leagueName": item.get("leagueName"),
        "team1": normalize_team(item.get("team1")),
        "team2": normalize_team(item.get("team2")),
        "finalScore": (
            {
                "team1": final.get("pointsTeam1"),
                "team2": final.get("pointsTeam2"),
                "label": final.get("resultName"),
            }
            if final
            else None
        ),
        "goals": [normalize_goal(g) for g in (item.get("goals") or [])],
    }


# ------------------------------------------------------------------
# Response-level normalizers
# ------------------------------------------------------------------


def normalize_leagues_response(raw: Any) -> Any:
    if not isinstance(raw, list):
        return []
    return [normalize_league(item) for item in raw]


def normalize_matches_response(raw: Any) -> Any:
    if not isinstance(raw, list):
        return []
    return [normalize_match(item) for item in raw]


def normalize_match_response(raw: Any) -> Any:
    if raw is None:
        return None
    # OpenLiga returns a list with one item for /getmatchdata/{matchId}.
    if isinstance(raw, list):
        return normalize_match(raw[0]) if raw else None
    if isinstance(raw, dict):
        return normalize_match(raw)
    return None
