# -*- coding: utf-8 -*-
"""Domain exceptions for the proxy layer."""


class ProxyError(Exception):
    status_code: int = 500
    code: str = "internal_error"

    def __init__(self, message: str, *, details: list[str] | None = None):
        super().__init__(message)
        self.message = message
        self.details = details or []


class UnknownOperationError(ProxyError):
    status_code = 400
    code = "unknown_operation"


class PayloadValidationError(ProxyError):
    status_code = 400
    code = "payload_validation_error"


class UpstreamFailedError(ProxyError):
    status_code = 502
    code = "upstream_failed"
