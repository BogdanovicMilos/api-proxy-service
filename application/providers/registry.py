# -*- coding: utf-8 -*-
"""Provider selection.

To add a new provider:
  1. Create application/providers/<name>/ with a SportsProvider subclass.
  2. Register it in `_PROVIDERS` below.
  3. Set SPORTS_PROVIDER=<name> in env to activate it.

Nothing else in the codebase needs to change.
"""
from typing import Callable

from application.config.settings import settings
from application.providers.base import SportsProvider
from application.providers.openliga import OpenLigaProvider

_PROVIDERS: dict[str, Callable[[], SportsProvider]] = {
    "openliga": OpenLigaProvider,
}


_instance: SportsProvider | None = None


def get_provider() -> SportsProvider:
    global _instance
    if _instance is not None:
        return _instance
    name = settings.sports_provider.lower()
    factory = _PROVIDERS.get(name)
    if factory is None:
        raise ValueError(
            f"Unknown sports provider '{settings.sports_provider}'. "
            f"Supported: {sorted(_PROVIDERS.keys())}"
        )
    _instance = factory()
    return _instance


async def shutdown_provider() -> None:
    global _instance
    if _instance is not None and hasattr(_instance, "aclose"):
        await _instance.aclose()  # type: ignore[func-returns-value]
    _instance = None


def supported_providers() -> list[str]:
    return sorted(_PROVIDERS.keys())
