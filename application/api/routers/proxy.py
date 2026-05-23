# -*- coding: utf-8 -*-
"""The single /proxy/execute endpoint.

Flow:
  1. Resolve operation from decision mapper.
  2. Validate payload using operation's pydantic schema.
  3. Invoke provider adapter; rate limit + retries live inside the adapter.
  4. Normalize response.
  5. Return structured response or structured error.
"""
import time

from fastapi import APIRouter, status
from fastapi.responses import JSONResponse

from application.logging.audit import audit
from application.logging.context import request_id_ctx
from application.providers.base import UpstreamError
from application.providers.registry import get_provider
from application.proxy.errors import (
    PayloadValidationError,
    ProxyError,
    UnknownOperationError,
    UpstreamFailedError,
)
from application.proxy.mapper import resolve_operation, validate_payload
from application.proxy.schemas import ErrorPayload, ProxyRequest, ProxyResponse

router = APIRouter(prefix="/proxy", tags=["proxy"])


def _error_response(exc: ProxyError) -> JSONResponse:
    payload = ErrorPayload(
        error=exc.message,
        code=exc.code,
        details=exc.details,
        request_id=request_id_ctx.get(),
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=payload.model_dump(by_alias=True),
    )


@router.post(
    "/execute",
    status_code=status.HTTP_200_OK,
    responses={
        400: {"model": ErrorPayload},
        502: {"model": ErrorPayload},
    },
)
async def execute(request: ProxyRequest) -> JSONResponse:
    rid = request_id_ctx.get()
    operation_type = request.operation_type
    audit(
        "proxy_dispatch_start",
        operationType=operation_type,
        payload_keys=sorted(request.payload.keys()),
    )

    # 1. Resolve operation.
    try:
        operation = resolve_operation(operation_type)
    except UnknownOperationError as exc:
        audit(
            "proxy_validation",
            operationType=operation_type,
            outcome="fail",
            reason="unknown_operation",
        )
        return _error_response(exc)

    # 2. Validate payload.
    try:
        validated = validate_payload(operation, request.payload)
    except PayloadValidationError as exc:
        audit(
            "proxy_validation",
            operationType=operation_type,
            outcome="fail",
            reasons=exc.details,
        )
        return _error_response(exc)

    audit(
        "proxy_validation",
        operationType=operation_type,
        outcome="pass",
    )

    # 3. Call provider.
    provider = get_provider()
    started = time.monotonic()
    try:
        result = await operation.call(provider, validated)
    except UpstreamError as exc:
        audit(
            "proxy_outcome",
            operationType=operation_type,
            provider=provider.name,
            target_url=exc.target_url,
            upstream_status=exc.status_code,
            attempts=exc.attempts,
            outcome="error",
            error_code="upstream_failed",
        )
        return _error_response(
            UpstreamFailedError(
                "Upstream API failed",
                details=[str(exc)],
            )
        )
    except Exception as exc:  # noqa: BLE001
        audit(
            "proxy_outcome",
            operationType=operation_type,
            provider=provider.name,
            outcome="error",
            error_code="internal_error",
            detail=str(exc),
        )
        return JSONResponse(
            status_code=500,
            content=ErrorPayload(
                error="Internal server error",
                code="internal_error",
                details=[type(exc).__name__],
                request_id=rid,
            ).model_dump(by_alias=True),
        )

    # 4. Normalize and respond.
    normalized = operation.normalize(result.data)
    audit(
        "proxy_outcome",
        operationType=operation_type,
        provider=provider.name,
        target_url=result.target_url,
        upstream_status=result.status_code,
        upstream_latency_ms=round(result.latency_ms, 2),
        total_ms=round((time.monotonic() - started) * 1000.0, 2),
        outcome="success",
    )
    response = ProxyResponse(request_id=rid, operation_type=operation_type, data=normalized)
    return JSONResponse(status_code=200, content=response.model_dump(by_alias=True))
