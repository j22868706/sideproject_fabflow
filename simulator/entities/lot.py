"""Domain model for a wafer lot."""

from dataclasses import dataclass
from enum import StrEnum


class LotPriority(StrEnum):
    """Supported wafer-lot priority levels."""

    NORMAL = "normal"
    HOT = "hot"


@dataclass(frozen=True)
class Lot:
    """A simplified wafer lot used by the simulation engine."""

    lot_id: str
    priority: LotPriority
    arrival_time: float
    due_date: float

    def __post_init__(self) -> None:
        """Validate the lot configuration."""
        if not self.lot_id.strip():
            raise ValueError("lot_id must not be empty")

        if self.arrival_time < 0:
            raise ValueError("arrival_time must be non-negative")

        if self.due_date < self.arrival_time:
            raise ValueError("due_date must not be earlier than arrival_time")
