# -*- coding: utf-8 -*-
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from application.api.middleware import RequestLoggingMiddleware
from application.api.routers.proxy import router as proxy_router
from application.logging.audit import audit, configure_logging
from application.providers.registry import shutdown_provider

VERSION = "0.1.0"
TITLE = "API Proxy Service"


@asynccontextmanager
async def lifespan(_app: FastAPI):
    configure_logging()
    audit("service_start", version=VERSION)
    try:
        yield
    finally:
        await shutdown_provider()
        audit("service_stop")


app = FastAPI(title=TITLE, version=VERSION, lifespan=lifespan)

app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(proxy_router)


@app.get("/healthcheck", operation_id="health_check")
def healthcheck():
    return {"message": "Ok"}
