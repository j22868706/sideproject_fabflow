"""Process liveness and application lifecycle readiness."""

from typing import Literal

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from app.api.errors import ErrorResponse
from app.services.runs import RunService

router = APIRouter(prefix="/health", tags=["health"])


class HealthResponse(BaseModel):
    status: Literal["alive", "ready"]


def is_ready(request: Request) -> bool:
    """Check lifecycle readiness and service presence without running a simulation."""
    return bool(getattr(request.app.state, "ready", False)) and isinstance(
        getattr(request.app.state, "run_service", None), RunService
    )


@router.get("/live", response_model=HealthResponse)
def live() -> HealthResponse:
    """Confirm that the application can respond, independently of readiness."""
    return HealthResponse(status="alive")


@router.get("/ready", response_model=HealthResponse, responses={503: {"model": ErrorResponse}})
def ready(request: Request) -> HealthResponse:
    """Return 503 until startup completes or when the run service is unavailable."""
    if not is_ready(request):
        raise HTTPException(status_code=503, detail="Service not ready")
    return HealthResponse(status="ready")
