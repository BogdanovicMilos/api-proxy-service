# -*- coding: utf-8 -*-
"""Structured audit logger.

Emits JSON lines to stdout with stable field names so logs can be grepped
and correlated by requestId.
"""
import json
import logging
import sys
import time
from typing import Any

from application.logging.context import request_id_ctx

audit_logger = logging.getLogger("audit")

_SENSITIVE_HEADERS = {"authorization", "cookie", "set-cookie", "x-api-key"}


def _redact_headers(headers: dict[str, str]) -> dict[str, str]:
    return {k: ("<redacted>" if k.lower() in _SENSITIVE_HEADERS else v) for k, v in headers.items()}


class _JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(record.created))
            + f".{int(record.msecs):03d}Z",
            "level": record.levelname,
            "logger": record.name,
            "requestId": request_id_ctx.get(),
            "msg": record.getMessage(),
        }
        extra = getattr(record, "audit", None)
        if isinstance(extra, dict):
            payload.update(extra)
        return json.dumps(payload, default=str)


def configure_logging() -> None:
    """Idempotently install the JSON handler on the root logger."""
    root = logging.getLogger()
    if getattr(root, "_audit_configured", False):
        return
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(_JsonFormatter())
    root.handlers = [handler]
    root.setLevel(logging.INFO)
    root._audit_configured = True  # type: ignore[attr-defined]


def audit(event: str, **fields: Any) -> None:
    """Emit a structured audit event."""
    if "headers" in fields and isinstance(fields["headers"], dict):
        fields["headers"] = _redact_headers(fields["headers"])
    audit_logger.info(event, extra={"audit": {"event": event, **fields}})


def truncate(body: bytes | str | None, limit: int) -> str:
    if body is None:
        return ""
    if isinstance(body, bytes):
        try:
            body = body.decode("utf-8", errors="replace")
        except Exception:
            body = repr(body)
    if len(body) <= limit:
        return body
    return body[:limit] + f"...<truncated {len(body) - limit} chars>"
