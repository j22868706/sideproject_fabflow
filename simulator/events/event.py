from dataclasses import dataclass
from enum import StrEnum


class EventType(StrEnum):
    MACHINE_FAILED = "MACHINE_FAILED"
    MACHINE_REPAIRED = "MACHINE_REPAIRED"
    LOT_ARRIVED = "LOT_ARRIVED"
    LOT_QUEUED = "LOT_QUEUED"
    PROCESS_STARTED = "PROCESS_STARTED"
    PROCESS_COMPLETED = "PROCESS_COMPLETED"
    LOT_COMPLETED = "LOT_COMPLETED"
    TRANSPORT_REQUESTED = "TRANSPORT_REQUESTED"
    TRANSPORT_STARTED = "TRANSPORT_STARTED"
    TRANSPORT_COMPLETED = "TRANSPORT_COMPLETED"


@dataclass(frozen=True)
class SimulationEvent:
    timestamp: float
    event_type: EventType
    lot_id: str | None
    machine_id: str | None = None
    queue_depth: int | None = None
    step_id: str | None = None
    transport_job_id: str | None = None
    origin: str | None = None
    destination: str | None = None
