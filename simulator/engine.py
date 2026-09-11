import random
from dataclasses import dataclass

import simpy

from simulator.entities.lot import Lot, LotStatus
from simulator.entities.machine import Machine, MachineStatus
from simulator.entities.queue import Queue
from simulator.events.event import EventType, SimulationEvent


@dataclass(frozen=True)
class SimulationResult:
    finished_at: float
    completed_lots: tuple[Lot, ...]
    events: tuple[SimulationEvent, ...]


class SimulationEngine:
    """Deterministic discrete-event simulation engine."""

    def __init__(self, seed: int) -> None:
        self.seed = seed
        self.random = random.Random(seed)
        self.env = simpy.Environment()
        self.events: list[SimulationEvent] = []
        self.completed_lots: list[Lot] = []

    def log_event(
        self,
        event_type: EventType,
        lot: Lot,
        machine: Machine | None = None,
        queue_depth: int | None = None,
    ) -> None:
        self.events.append(
            SimulationEvent(
                timestamp=float(self.env.now),
                event_type=event_type,
                lot_id=lot.lot_id,
                machine_id=machine.machine_id if machine else None,
                queue_depth=queue_depth,
            )
        )

    def process_lot(
        self,
        lot: Lot,
        machine: Machine,
        queue: Queue,
    ):
        yield self.env.timeout(lot.arrival_time)

        self.log_event(
            event_type=EventType.LOT_ARRIVED,
            lot=lot,
        )

        lot.status = LotStatus.WAITING
        queue.enqueue(lot)

        self.log_event(
            event_type=EventType.LOT_QUEUED,
            lot=lot,
            queue_depth=queue.depth,
        )

        with machine.resource.request() as request:
            yield request

            queue.dequeue(lot)
            lot.status = LotStatus.PROCESSING
            lot.started_at = float(self.env.now)

            machine.status = MachineStatus.BUSY
            machine.current_lot = lot

            self.log_event(
                event_type=EventType.PROCESS_STARTED,
                lot=lot,
                machine=machine,
                queue_depth=queue.depth,
            )

            processing_time = lot.current_process_step.processing_time

            yield self.env.timeout(processing_time)

            machine.busy_time += processing_time

            self.log_event(
                event_type=EventType.PROCESS_COMPLETED,
                lot=lot,
                machine=machine,
            )

            lot.current_step += 1
            lot.status = LotStatus.COMPLETED
            lot.completed_at = float(self.env.now)

            machine.status = MachineStatus.IDLE
            machine.current_lot = None

            self.completed_lots.append(lot)

            self.log_event(
                event_type=EventType.LOT_COMPLETED,
                lot=lot,
                machine=machine,
            )

    def run(
        self,
        lots: list[Lot],
        machine: Machine,
        queue: Queue,
    ) -> SimulationResult:
        for lot in lots:
            self.env.process(
                self.process_lot(
                    lot=lot,
                    machine=machine,
                    queue=queue,
                )
            )

        self.env.run()

        return SimulationResult(
            finished_at=float(self.env.now),
            completed_lots=tuple(self.completed_lots),
            events=tuple(self.events),
        )
