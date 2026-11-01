"""Storage contracts for completed simulation results."""

from dataclasses import dataclass
from threading import Lock
from typing import Protocol

from app.models.simulation import EventResponse, MetricsResponse, RunResponse


class RunStoreError(Exception):
    """A storage operation failed."""


class RunStoreUnavailable(RunStoreError):
    """The storage backend is temporarily unavailable."""


class RunAlreadyExists(RunStoreError):
    """A completed result already exists with this run ID."""


@dataclass(frozen=True)
class StoredRun:
    """Complete responses belonging to one finished simulation."""

    summary: RunResponse
    metrics: MetricsResponse
    events: tuple[EventResponse, ...]


class RunStore(Protocol):
    """Storage interface for completed simulation results."""

    def save(self, run: StoredRun) -> None:
        """Save a complete result; return only after successful storage."""
        ...

    def get(self, run_id: str) -> StoredRun | None:
        """Return a stored result, or None when the ID does not exist."""
        ...


class MemoryRunStore:
    """Keep completed results in this process's memory."""

    def __init__(self) -> None:
        self._runs: dict[str, StoredRun] = {}
        self._lock = Lock()

    def save(self, run: StoredRun) -> None:
        with self._lock:
            run_id = run.summary.run_id
            if run_id in self._runs:
                raise RunAlreadyExists(f"Run already exists: {run_id}")
            self._runs[run_id] = run

    def get(self, run_id: str) -> StoredRun | None:
        with self._lock:
            return self._runs.get(run_id)
