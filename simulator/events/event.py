from dataclasses import dataclass
from enum import StrEnum


class EventType(StrEnum):
    LOT_ARRIVED = "LOT_ARRIVED"
    LOT_QUEUED = "LOT_QUEUED"
    PROCESS_STARTED = "PROCESS_STARTED"
    PROCESS_COMPLETED = "PROCESS_COMPLETED"
    LOT_COMPLETED = "LOT_COMPLETED"


@dataclass(frozen=True)
class SimulationEvent:
    timestamp: float
    event_type: EventType
    lot_id: str
    machine_id: str | None = None
    queue_depth: int | None = None
    step_id: str | None = None
