# -*- coding: utf-8 -*-
"""Request/response recording middleware.

Logs inbound + outbound metadata as structured audit events, generates
a requestId if the client did not provide one, and correlates every
log line emitted during the request lifecycle via the request-id ContextVar.
"""
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from application.config.settings import settings
from application.logging.audit import audit, truncate
from application.logging.context import request_id_ctx

REQUEST_ID_HEADER = "x-request-id"


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        rid = request.headers.get(REQUEST_ID_HEADER) or str(uuid.uuid4())
        token = request_id_ctx.set(rid)

        body = await request.body()

        async def _receive():
            return {"type": "http.request", "body": body, "more_body": False}

        request = Request(request.scope, _receive)

        audit(
            "request_in",
            method=request.method,
            path=request.url.path,
            query=str(request.url.query) or None,
            headers=dict(request.headers),
            body_size=len(body),
            body_preview=truncate(body, settings.log_body_truncate_chars),
        )

        start = time.monotonic()
        try:
            response = await call_next(request)
        except Exception as exc:  # noqa: BLE001
            duration_ms = (time.monotonic() - start) * 1000.0
            audit(
                "request_error",
                error=type(exc).__name__,
                detail=str(exc),
                duration_ms=round(duration_ms, 2),
            )
            request_id_ctx.reset(token)
            raise

        body_chunks: list[bytes] = []
        async for chunk in response.body_iterator:
            body_chunks.append(chunk)
        resp_body = b"".join(body_chunks)

        duration_ms = (time.monotonic() - start) * 1000.0
        audit(
            "request_out",
            status_code=response.status_code,
            body_size=len(resp_body),
            body_preview=truncate(resp_body, settings.log_body_truncate_chars),
            duration_ms=round(duration_ms, 2),
        )

        headers = dict(response.headers)
        headers[REQUEST_ID_HEADER] = rid
        request_id_ctx.reset(token)
        return Response(
            content=resp_body,
            status_code=response.status_code,
            headers=headers,
            media_type=response.media_type,
        )
