# -*- coding: utf-8 -*-
"""Request-scoped context for correlating logs across the request lifecycle."""
from contextvars import ContextVar

request_id_ctx: ContextVar[str] = ContextVar("request_id", default="-")
