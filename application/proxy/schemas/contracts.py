# -*- coding: utf-8 -*-
"""Top-level wire contracts: request envelope, response envelope, error envelope.

Wire format stays camelCase for JSON clients; Python attributes are snake_case.
Aliases bridge the two — Pydantic translates on parse and serialize.
"""
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ProxyRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    operation_type: str = Field(..., alias="operationType", min_length=1)
    payload: dict[str, Any] = Field(default_factory=dict)


class ProxyResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    request_id: str = Field(..., serialization_alias="requestId")
    operation_type: str = Field(..., serialization_alias="operationType")
    data: Any


class ErrorPayload(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    error: str
    code: str
    details: list[str] = Field(default_factory=list)
    request_id: str = Field(..., serialization_alias="requestId")
