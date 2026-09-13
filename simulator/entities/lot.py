from dataclasses import dataclass, field
from enum import StrEnum

from simulator.entities.process_step import ProcessStep


class LotPriority(StrEnum):
    """Priority level assigned to a wafer lot."""

    NORMAL = "NORMAL"
    HOT = "HOT"


class LotStatus(StrEnum):
    """Current lifecycle state of a wafer lot."""

    CREATED = "CREATED"
    WAITING = "WAITING"
    PROCESSING = "PROCESSING"
    WAITING_FOR_TRANSPORT = "WAITING_FOR_TRANSPORT"
    IN_TRANSPORT = "IN_TRANSPORT"
    COMPLETED = "COMPLETED"


@dataclass
class Lot:
    """A wafer lot moving through the simulated manufacturing system."""

    lot_id: str
    arrival_time: float
    due_date: float
    route: list[ProcessStep] = field(default_factory=list)
    priority: LotPriority = LotPriority.NORMAL
    current_step: int = 0
    status: LotStatus = LotStatus.CREATED
    started_at: float | None = None
    completed_at: float | None = None

    def __post_init__(self) -> None:
        if not self.lot_id.strip():
            raise ValueError("lot_id must not be empty")

        if self.arrival_time < 0:
            raise ValueError("arrival_time must be non-negative")

        if self.due_date < self.arrival_time:
            raise ValueError("due_date must not be earlier than arrival_time")

    @property
    def current_process_step(self) -> ProcessStep:
        if not self.route:
            raise IndexError("lot does not have a process route")

        if self.current_step >= len(self.route):
            raise IndexError("lot has completed every process step")

        return self.route[self.current_step]

    @property
    def cycle_time(self) -> float | None:
        if self.completed_at is None:
            return None

        return self.completed_at - self.arrival_time
