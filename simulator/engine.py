import random
from copy import deepcopy
from dataclasses import dataclass

import simpy

from simulator.entities.lot import Lot, LotStatus
from simulator.entities.machine import Machine, MachineStatus
from simulator.entities.queue import Queue
from simulator.entities.scenario import SimulationScenario
from simulator.entities.transport import TransportConfig, TransportJob
from simulator.events.event import EventType, SimulationEvent
from simulator.metrics.kpi import KPIResult, MachineSummary, calculate_kpis
from simulator.policies.base import DispatchCandidate, DispatchPolicy
from simulator.policies.fifo import FIFOPolicy
from simulator.policies.hot_lot import HotLotPolicy


@dataclass(frozen=True)
class SimulationResult:
    finished_at: float
    completed_lots: tuple[Lot, ...]
    events: tuple[SimulationEvent, ...]
    machines: tuple[MachineSummary, ...] = ()
    transport_jobs: tuple[TransportJob, ...] = ()
    vehicle_count: int = 0

    @property
    def kpis(self) -> KPIResult:
        return calculate_kpis(self)

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
    """One-shot, deterministic policy dispatch across eligible machine groups."""

    def __init__(
        self,
        seed: int,
        policy: DispatchPolicy | None = None,
        *,
        normal_wait_threshold: float = 60.0,
    ) -> None:
        self.policy = HotLotPolicy(
            policy if policy is not None else FIFOPolicy(), normal_wait_threshold
        )
        self.seed = seed
        self.random = random.Random(seed)
        self.env = simpy.Environment()
        self.events: list[SimulationEvent] = []
        self.completed_lots: list[Lot] = []
        self.machines: list[Machine] = []
        self.queues: dict[str, Queue] = {}
        self._slots: dict[str, simpy.FilterStore] = {}
        self._waiting: dict[str, list[DispatchCandidate]] = {}
        self._wake: dict[str, simpy.Event] = {}
        self._assignments: dict[str, simpy.Event] = {}
        self._sequence = 0
        self._has_run = False
        self.transport: TransportConfig | None = None
        self.vehicles: simpy.Resource | None = None
        self.transport_jobs: list[TransportJob] = []
        self._transport_sequence = 0

    def log_event(
        self,
        event_type: EventType,
        lot: Lot | None,
        machine: Machine | None = None,
        queue_depth: int | None = None,
        step_id: str | None = None,
    ) -> None:
        self.events.append(
            SimulationEvent(
                timestamp=float(self.env.now),
                event_type=event_type,
                lot_id=lot.lot_id if lot else None,
                machine_id=machine.machine_id if machine else None,
                queue_depth=queue_depth,
                step_id=step_id,
            )
        )

    def dispatch_group(self, group: str):
        """Choose from the station queue when an eligible capacity slot is free."""
        while True:
            while not self._waiting[group]:
                yield self._wake[group]
                self._wake[group] = self.env.event()
            machine = yield self._slots[group].get(lambda item: item.status != MachineStatus.DOWN)
            candidate = self.policy.select(tuple(self._waiting[group]), float(self.env.now))
            if not any(candidate is waiting for waiting in self._waiting[group]):
                raise ValueError("policy must return one of the supplied candidates")
            self._waiting[group].remove(candidate)
            self._assignments.pop(candidate.lot.lot_id).succeed(machine)

    def process_operation(self, machine: Machine, duration: float):
        remaining = duration
        while remaining > 0:
            if machine.status == MachineStatus.DOWN:
                yield machine.repaired
            started = float(self.env.now)
            completed = self.env.timeout(remaining)
            outcome = yield completed | machine.failed
            remaining = (
                0.0
                if completed in outcome
                else max(0.0, remaining - (float(self.env.now) - started))
            )

    def fail_machine(self, machine: Machine, rng: random.Random):
        config = machine.reliability
        assert config is not None
        index = 0
        while True:
            if config.mtbf is not None:
                start = float(self.env.now) + rng.expovariate(1 / config.mtbf)
                duration = rng.expovariate(1 / config.mttr)
            elif index < len(config.outages):
                start, duration = config.outages[index]
                index += 1
            else:
                return
            yield self.env.timeout(start - float(self.env.now))
            machine.status = MachineStatus.DOWN
            machine.repaired = self.env.event()
            machine.failed.succeed()
            self.log_event(EventType.MACHINE_FAILED, None, machine)
            yield self.env.timeout(duration)
            machine.downtime += duration
            machine.failed = self.env.event()
            machine.status = MachineStatus.BUSY if machine.active_lots else MachineStatus.IDLE
            self.log_event(EventType.MACHINE_REPAIRED, None, machine)
            machine.repaired.succeed()
            # Reinsert idle tokens to wake filtered requests after the status change.
            slots = self._slots[machine.group]
            idle = [item for item in slots.items if item is machine]
            slots.items[:] = [item for item in slots.items if item is not machine]
            for item in idle:
                slots.put(item)

    def transport_lot(self, lot: Lot, origin: str, destination: str):
        assert self.transport is not None and self.vehicles is not None
        self._transport_sequence += 1
        job_id = f"TRANSPORT-{self._transport_sequence:05d}"
        requested = float(self.env.now)

        def record(event_type: EventType) -> None:
            self.events.append(
                SimulationEvent(
                    timestamp=float(self.env.now),
                    event_type=event_type,
                    lot_id=lot.lot_id,
                    queue_depth=len(self.vehicles.queue),
                    transport_job_id=job_id,
                    origin=origin,
                    destination=destination,
                )
            )

        lot.status = LotStatus.WAITING_FOR_TRANSPORT
        with self.vehicles.request() as request:
            record(EventType.TRANSPORT_REQUESTED)
            yield request
            pickup = float(self.env.now)
            lot.status = LotStatus.IN_TRANSPORT
            record(EventType.TRANSPORT_STARTED)
            yield self.env.timeout(self.transport.travel_time)
            self.transport_jobs.append(
                TransportJob(
                    job_id, lot.lot_id, origin, destination, requested, pickup, float(self.env.now)
                )
            )
            record(EventType.TRANSPORT_COMPLETED)

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

            assignment = self.env.event()
            self._assignments[lot.lot_id] = assignment
            self._waiting[group].append(DispatchCandidate(lot, float(self.env.now), self._sequence))
            self._sequence += 1
            if not self._wake[group].triggered:
                self._wake[group].succeed()
            machine = yield assignment
            with machine.resource.request() as request:
                yield request
                if machine.status == MachineStatus.DOWN:
                    yield machine.repaired
                queue.dequeue(lot)
                lot.status = LotStatus.PROCESSING
                if lot.started_at is None:
                    lot.started_at = float(self.env.now)
                machine.active_lots.append(lot)
                machine.current_lot = machine.active_lots[0]
                machine.status = MachineStatus.BUSY
                self.log_event(EventType.PROCESS_STARTED, lot, machine, queue.depth, step.step_id)
                yield self.env.process(self.process_operation(machine, step.processing_time))
                machine.busy_time += step.processing_time
                self.log_event(EventType.PROCESS_COMPLETED, lot, machine, step_id=step.step_id)
                lot.current_step += 1
                machine.active_lots.remove(lot)
                machine.current_lot = machine.active_lots[0] if machine.active_lots else None
                if machine.status != MachineStatus.DOWN:
                    machine.status = (
                        MachineStatus.BUSY if machine.active_lots else MachineStatus.IDLE
                    )
            self._slots[group].put(machine)
            if self.transport is not None and lot.current_step < len(lot.route):
                yield self.env.process(
                    self.transport_lot(lot, group, lot.current_process_step.eligible_machine_group)
                )

        lot.status = LotStatus.COMPLETED
        lot.completed_at = float(self.env.now)
        self.completed_lots.append(lot)
        self.log_event(EventType.LOT_COMPLETED, lot, machine)

    def run_scenario(self, scenario: SimulationScenario) -> SimulationResult:
        if scenario.seed != self.seed:
            raise ValueError("scenario seed must match engine seed")
        machines = [
            Machine(
                self.env,
                config.machine_id,
                config.group,
                config.capacity,
                reliability=config.reliability,
            )
            for config in scenario.machines
        ]
        self.transport = scenario.transport
        if self.transport is not None:
            self.vehicles = simpy.Resource(self.env, capacity=self.transport.vehicle_count)
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
            slots = simpy.FilterStore(self.env)
            for machine in machines:
                if machine.group == group:
                    for _ in range(machine.capacity):
                        slots.put(machine)
            self._slots[group] = slots
            self._waiting[group] = []
            self._wake[group] = self.env.event()
            self.env.process(self.dispatch_group(group))
        for machine in sorted(machines, key=lambda item: item.machine_id):
            if machine.reliability is not None:
                rng = random.Random(self.random.getrandbits(128))
                self.env.process(self.fail_machine(machine, rng))
        processes = [self.env.process(self.process_lot(lot)) for lot in lots]
        if processes:
            self.env.run(until=self.env.all_of(processes))
        return SimulationResult(
            float(self.env.now),
            tuple(self.completed_lots),
            tuple(self.events),
            tuple(MachineSummary(m.machine_id, m.capacity, m.busy_time) for m in machines),
            tuple(self.transport_jobs),
            self.transport.vehicle_count if self.transport else 0,
        )
