"""ASGI entry point: uvicorn app.main:app."""

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError

from app.api.errors import (
    storage_unavailable_handler,
    unexpected_error_handler,
    validation_error_handler,
)
from app.api.health import router as health_router
from app.api.runs import router
from app.services.postgres_run_store import PostgresRunStore
from app.services.run_store import MemoryRunStore, RunStore, RunStoreUnavailable
from app.services.runs import RunService


@asynccontextmanager
async def lifespan(application: FastAPI):
    """Expose readiness during the ASGI lifespan and clear it during shutdown."""
    application.state.ready = True
    try:
        yield
    finally:
        application.state.ready = False


def create_app(store: RunStore | None = None) -> FastAPI:
    """Create an API instance with the selected result store."""
    if store is None:
        backend = os.getenv("FABFLOW_RUN_STORE", "memory")
        if backend == "memory":
            store = MemoryRunStore()
        elif backend == "postgres":
            store = PostgresRunStore()
        else:
            raise ValueError("FABFLOW_RUN_STORE must be 'memory' or 'postgres'")

    application = FastAPI(title="FabFlow", version="0.1.0", lifespan=lifespan)
    application.state.ready = False
    application.state.run_service = RunService(store)
    application.add_exception_handler(RequestValidationError, validation_error_handler)
    application.add_exception_handler(Exception, unexpected_error_handler)
    application.add_exception_handler(RunStoreUnavailable, storage_unavailable_handler)
    application.include_router(router)
    application.include_router(health_router)
    return application


app = create_app()
