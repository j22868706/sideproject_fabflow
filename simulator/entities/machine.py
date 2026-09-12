from dataclasses import dataclass, field
from enum import StrEnum

import simpy

from simulator.entities.lot import Lot


class MachineStatus(StrEnum):
    IDLE = "IDLE"
    BUSY = "BUSY"


@dataclass
class Machine:
    """A processing machine with finite capacity."""

    env: simpy.Environment
    machine_id: str
    group: str
    capacity: int = 1
    status: MachineStatus = MachineStatus.IDLE
    current_lot: Lot | None = None
    active_lots: list[Lot] = field(default_factory=list)
    busy_time: float = 0.0
    resource: simpy.Resource = field(init=False)

    def __post_init__(self) -> None:
        if not self.machine_id:
            raise ValueError("machine_id must not be empty")

        if not self.group:
            raise ValueError("group must not be empty")

        if self.capacity <= 0:
            raise ValueError("capacity must be greater than zero")

        self.resource = simpy.Resource(
            self.env,
            capacity=self.capacity,
        )
