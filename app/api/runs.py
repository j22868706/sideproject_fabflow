"""Create simulations and query completed results."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

from app.api.errors import ErrorResponse, ValidationErrorResponse
from app.api.health import is_ready
from app.models.simulation import EventResponse, MetricsResponse, RunCreate, RunResponse
from app.services.runs import RunService, StoredRun

router = APIRouter(
    prefix="/api/v1/runs",
    tags=["runs"],
    responses={
        404: {"model": ErrorResponse},
        422: {"model": ValidationErrorResponse},
        500: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
    },
)


def get_run_service(request: Request) -> RunService:
    """Reject run access until the application is ready to serve requests."""
    if not is_ready(request):
        raise HTTPException(status_code=503, detail="Service not ready")
    return request.app.state.run_service


Service = Annotated[RunService, Depends(get_run_service)]


def get_stored_run(run_id: str, service: Service) -> StoredRun:
    """Resolve a completed run or return the shared 404 response."""
    stored = service.get(run_id)
    if stored is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return stored


ExistingRun = Annotated[StoredRun, Depends(get_stored_run)]


@router.post("", response_model=RunResponse, status_code=status.HTTP_201_CREATED)
def create_run(payload: RunCreate, response: Response, service: Service) -> RunResponse:
    """Finish the simulation before returning its summary and query location."""
    stored = service.create(payload)
    response.headers["Location"] = f"/api/v1/runs/{stored.summary.run_id}"
    return stored.summary


@router.get("/{run_id}", response_model=RunResponse)
def get_run(stored: ExistingRun) -> RunResponse:
    """Return the completion summary and settings recorded for this run."""
    return stored.summary


@router.get("/{run_id}/metrics", response_model=MetricsResponse)
def get_metrics(stored: ExistingRun) -> MetricsResponse:
    """Return manufacturing, machine, and transport KPIs for the full run."""
    return stored.metrics


@router.get("/{run_id}/events", response_model=list[EventResponse])
def get_events(stored: ExistingRun) -> tuple[EventResponse, ...]:
    """Return all recorded events in their original simulation order."""
    return stored.events
