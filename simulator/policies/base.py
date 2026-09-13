from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol

from simulator.entities.lot import Lot


@dataclass(frozen=True)
class DispatchCandidate:
    """A waiting lot and its arrival order at the current station."""

    lot: Lot
    queued_at: float
    sequence: int


class DispatchPolicy(Protocol):
    """Select one candidate without modifying the waiting queue."""

    def select(
        self,
        candidates: Sequence[DispatchCandidate],
        current_time: float,
    ) -> DispatchCandidate:
        """Return a candidate, or raise ValueError if the queue is empty."""
        ...
