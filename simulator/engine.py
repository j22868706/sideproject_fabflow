import random
from copy import deepcopy
from dataclasses import dataclass

import simpy

from simulator.entities.lot import Lot, LotStatus
from simulator.entities.machine import Machine, MachineStatus
from simulator.entities.queue import Queue
from simulator.entities.scenario import SimulationScenario
from simulator.events.event import EventType, SimulationEvent


@dataclass(frozen=True)
class SimulationResult:
    finished_at: float
    completed_lots: tuple[Lot, ...]
    events: tuple[SimulationEvent, ...]

    @property
    def average_cycle_time(self) -> float:
        if not self.completed_lots:
            return 0.0
        return sum(lot.cycle_time for lot in self.completed_lots) / len(self.completed_lots)

    @property
    def throughput_per_hour(self) -> float:
        """Completed lots per hour over [0, finished_at], with time in minutes."""
        return len(self.completed_lots) * 60 / self.finished_at if self.finished_at else 0.0


class SimulationEngine:
    """One-shot, deterministic FIFO simulation across eligible machine groups."""

    def __init__(self, seed: int) -> None:
        self.seed = seed
        self.random = random.Random(seed)
        self.env = simpy.Environment()
        self.events: list[SimulationEvent] = []
        self.completed_lots: list[Lot] = []
        self.machines: list[Machine] = []
        self.queues: dict[str, Queue] = {}
        self._slots: dict[str, simpy.Store] = {}
        self._has_run = False

    def log_event(
        self,
        event_type: EventType,
        lot: Lot,
        machine: Machine | None = None,
        queue_depth: int | None = None,
        step_id: str | None = None,
    ) -> None:
        self.events.append(
            SimulationEvent(
                timestamp=float(self.env.now),
                event_type=event_type,
                lot_id=lot.lot_id,
                machine_id=machine.machine_id if machine else None,
                queue_depth=queue_depth,
                step_id=step_id,
            )
        )

    def process_lot(self, lot: Lot):
        yield self.env.timeout(lot.arrival_time)
        self.log_event(EventType.LOT_ARRIVED, lot)
        machine = None
        for step in lot.route:
            group = step.eligible_machine_group
            queue = self.queues[group]
            lot.status = LotStatus.WAITING
            queue.enqueue(lot)
            self.log_event(EventType.LOT_QUEUED, lot, queue_depth=queue.depth, step_id=step.step_id)

            # Each token represents one available capacity slot on a real machine.
            machine = yield self._slots[group].get()
            with machine.resource.request() as request:
                yield request
                queue.dequeue(lot)
                lot.status = LotStatus.PROCESSING
                if lot.started_at is None:
                    lot.started_at = float(self.env.now)
                machine.active_lots.append(lot)
                machine.current_lot = machine.active_lots[0]
                machine.status = MachineStatus.BUSY
                self.log_event(EventType.PROCESS_STARTED, lot, machine, queue.depth, step.step_id)
                yield self.env.timeout(step.processing_time)
                machine.busy_time += step.processing_time
                self.log_event(EventType.PROCESS_COMPLETED, lot, machine, step_id=step.step_id)
                lot.current_step += 1
                machine.active_lots.remove(lot)
                machine.current_lot = machine.active_lots[0] if machine.active_lots else None
                machine.status = MachineStatus.BUSY if machine.active_lots else MachineStatus.IDLE
            self._slots[group].put(machine)

        lot.status = LotStatus.COMPLETED
        lot.completed_at = float(self.env.now)
        self.completed_lots.append(lot)
        self.log_event(EventType.LOT_COMPLETED, lot, machine)

    def run_scenario(self, scenario: SimulationScenario) -> SimulationResult:
        if scenario.seed != self.seed:
            raise ValueError("scenario seed must match engine seed")
        machines = [
            Machine(self.env, config.machine_id, config.group, config.capacity)
            for config in scenario.machines
        ]
        # Isolate mutable runtime state so a scenario can be executed repeatedly.
        return self._run(deepcopy(list(scenario.lots)), machines)

    def run(self, lots: list[Lot], machine: Machine, queue: Queue) -> SimulationResult:
        """Compatibility entry point for existing single-machine scenarios."""
        return self._run(lots, [machine], {machine.group: queue})

    def _run(
        self, lots: list[Lot], machines: list[Machine], queues: dict[str, Queue] | None = None
    ) -> SimulationResult:
        if self._has_run:
            raise ValueError("create a fresh engine for each run")
        groups = {machine.group for machine in machines}
        if any(machine.env is not self.env for machine in machines):
            raise ValueError("machines must belong to the engine environment")
        if len({lot.lot_id for lot in lots}) != len(lots):
            raise ValueError("lot_id must be unique")
        for lot in lots:
            if lot.status != LotStatus.CREATED or lot.current_step != 0:
                raise ValueError("lots must be fresh and unprocessed")
            if not lot.route or any(
                step.eligible_machine_group not in groups for step in lot.route
            ):
                raise ValueError("each route step must have an eligible machine")
        self._has_run = True
        self.machines = machines
        self.queues = (
            queues
            if queues is not None
            else {group: Queue(queue_id=f"QUEUE-{group}") for group in sorted(groups)}
        )
        for group in sorted(groups):
            slots = simpy.Store(self.env)
            for machine in machines:
                if machine.group == group:
                    for _ in range(machine.capacity):
                        slots.put(machine)
            self._slots[group] = slots
        for lot in lots:
            self.env.process(self.process_lot(lot))
        self.env.run()
        return SimulationResult(float(self.env.now), tuple(self.completed_lots), tuple(self.events))
