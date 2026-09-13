"""Manufacturing KPIs over [0, last lot completion], in minutes."""

from dataclasses import dataclass
from math import ceil
from typing import TYPE_CHECKING

from simulator.events.event import EventType

if TYPE_CHECKING:
    from simulator.engine import SimulationResult


@dataclass(frozen=True)
class MachineSummary:
    machine_id: str
    capacity: int
    busy_time: float


@dataclass(frozen=True)
class MachineKPI:
    machine_id: str
    utilization: float
    availability: float
    downtime: float


@dataclass(frozen=True)
class KPIResult:
    completed_lots: int
    observation_minutes: float
    average_cycle_time: float
    p95_cycle_time: float
    throughput_per_hour: float
    average_wip: float
    average_waiting_time: float
    average_queue_depth: float
    max_queue_depth: int
    on_time_delivery_rate: float
    average_tardiness: float
    machines: tuple[MachineKPI, ...]
    average_transport_time: float = 0.0
    average_transport_waiting_time: float = 0.0
    vehicle_utilization: float = 0.0
    transport_job_count: int = 0


def calculate_kpis(result: SimulationResult) -> KPIResult:
    horizon = result.finished_at
    lots = result.completed_lots
    cycles = sorted(lot.cycle_time for lot in lots)
    count = len(lots)
    waiting: dict[str, float] = {}
    wait_total = 0.0
    depth = peak = 0
    down: dict[str, float] = {}
    downtime: dict[str, float] = {}
    for event in result.events:
        if event.event_type == EventType.LOT_QUEUED:
            waiting[event.lot_id] = event.timestamp
            depth += 1
            peak = max(peak, depth)
        elif event.event_type == EventType.PROCESS_STARTED:
            wait_total += event.timestamp - waiting.pop(event.lot_id)
            depth -= 1
        elif event.event_type == EventType.MACHINE_FAILED:
            down[event.machine_id] = event.timestamp
        elif event.event_type == EventType.MACHINE_REPAIRED:
            downtime[event.machine_id] = downtime.get(event.machine_id, 0) + (
                event.timestamp - down.pop(event.machine_id)
            )
    for machine_id, start in down.items():
        downtime[machine_id] = downtime.get(machine_id, 0) + horizon - start
    machines = tuple(
        MachineKPI(
            machine.machine_id,
            machine.busy_time / (machine.capacity * horizon) if horizon else 0.0,
            1 - downtime.get(machine.machine_id, 0) / horizon if horizon else 1.0,
            downtime.get(machine.machine_id, 0.0),
        )
        for machine in result.machines
    )
    jobs = result.transport_jobs
    transport_busy = sum(job.transport_time for job in jobs)
    return KPIResult(
        count,
        horizon,
        sum(cycles) / count if count else 0.0,
        cycles[ceil(0.95 * count) - 1] if count else 0.0,
        count * 60 / horizon if horizon else 0.0,
        sum(cycles) / horizon if horizon else 0.0,
        wait_total / count if count else 0.0,
        wait_total / horizon if horizon else 0.0,
        peak,
        sum(lot.completed_at <= lot.due_date for lot in lots) / count if count else 0.0,
        sum(max(0, lot.completed_at - lot.due_date) for lot in lots) / count if count else 0.0,
        machines,
        transport_busy / len(jobs) if jobs else 0.0,
        sum(job.waiting_time for job in jobs) / len(jobs) if jobs else 0.0,
        transport_busy / (result.vehicle_count * horizon)
        if result.vehicle_count and horizon
        else 0.0,
        len(jobs),
    )
