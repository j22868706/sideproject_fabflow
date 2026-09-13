from dataclasses import dataclass, field
from enum import StrEnum

import simpy

from simulator.entities.lot import Lot
from simulator.entities.reliability import ReliabilityConfig


class MachineStatus(StrEnum):
    IDLE = "IDLE"
    BUSY = "BUSY"
    DOWN = "DOWN"


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
    reliability: ReliabilityConfig | None = None
    downtime: float = 0.0
    failed: simpy.Event = field(init=False)
    repaired: simpy.Event = field(init=False)
    resource: simpy.Resource = field(init=False)

    def __post_init__(self) -> None:
        if not self.machine_id:
            raise ValueError("machine_id must not be empty")

        if not self.group:
            raise ValueError("group must not be empty")

        if self.capacity <= 0:
            raise ValueError("capacity must be greater than zero")

        self.failed = self.env.event()
        self.repaired = self.env.event()
        self.resource = simpy.Resource(
            self.env,
            capacity=self.capacity,
        )
