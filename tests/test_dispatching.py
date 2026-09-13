import pytest

from simulator.engine import SimulationEngine
from simulator.entities.lot import Lot
from simulator.entities.machine import MachineStatus
from simulator.entities.process_step import ProcessStep
from simulator.entities.scenario import MachineConfig, SimulationScenario
from simulator.events.event import EventType
from simulator.policies.base import DispatchCandidate
from simulator.policies.critical_ratio import CriticalRatioPolicy
from simulator.policies.fifo import FIFOPolicy
from simulator.policies.spt import SPTPolicy


def candidate(lot_id, durations, due=100, queued=0, sequence=0, current_step=0):
    lot = Lot(
        lot_id,
        0,
        due,
        [ProcessStep(f"S{i}", "Station", duration, "G") for i, duration in enumerate(durations)],
        current_step=current_step,
    )
    return DispatchCandidate(lot, queued, sequence)


def test_spt_uses_current_operation_not_total_route():
    short = candidate("short", [20, 2, 30], current_step=1)
    long = candidate("long", [4])
    assert SPTPolicy().select([long, short], 0) is short


def test_cr_uses_only_remaining_route_and_recalculates_at_dispatch():
    first = candidate("A", [100, 10], due=20, current_step=1)
    second = candidate("B", [2, 3], due=12)
    policy = CriticalRatioPolicy()
    assert policy.select([second, first], 0) is first  # 2 < 2.4
    assert policy.select([first, second], 10) is second  # 0.4 < 1
    assert policy.select([first, second], 15) is second  # overdue: -0.6 < 0.5


@pytest.mark.parametrize("policy", [FIFOPolicy(), SPTPolicy(), CriticalRatioPolicy()])
def test_policy_fifo_ties_purity_and_empty_queue(policy):
    first = candidate("Z", [5], queued=1, sequence=0)
    second = candidate("A", [5], queued=1, sequence=1)
    later = candidate("B", [5], queued=2, sequence=0)
    candidates = [later, second, first]
    assert policy.select(candidates, 3) is first
    assert candidates == [later, second, first]
    with pytest.raises(ValueError, match="empty queue"):
        policy.select([], 3)


def test_cr_rejects_completed_candidate():
    with pytest.raises(ValueError, match="remaining processing time"):
        CriticalRatioPolicy().select([candidate("done", [5], current_step=1)], 10)


@pytest.mark.parametrize(
    ("policy", "order", "starts"),
    [
        (FIFOPolicy(), ["blocker", "long", "short", "urgent"], [0, 10, 16, 18]),
        (SPTPolicy(), ["blocker", "short", "urgent", "long"], [0, 10, 12, 16]),
        (CriticalRatioPolicy(), ["blocker", "urgent", "long", "short"], [0, 10, 14, 20]),
    ],
)
def test_engine_selects_waiting_lots_when_machine_becomes_available(policy, order, starts):
    steps = tuple(
        ProcessStep(str(i), "Station", duration, "G") for i, duration in enumerate([10, 6, 2, 4])
    )
    lots = tuple(
        Lot(name, arrival, due, [step])
        for name, arrival, due, step in zip(
            ["blocker", "long", "short", "urgent"],
            [0, 1, 2, 3],
            [100, 100, 100, 8],
            steps,
            strict=True,
        )
    )
    scenario = SimulationScenario("dispatch", 42, steps, (MachineConfig("M", "G"),), lots)
    engine = SimulationEngine(42, policy=policy)
    result = engine.run_scenario(scenario)
    events = [event for event in result.events if event.event_type == EventType.PROCESS_STARTED]
    assert [event.lot_id for event in events] == order
    assert [event.timestamp for event in events] == starts
    assert [event.queue_depth for event in events] == [0, 2, 1, 0]
    assert result.finished_at == 22
    assert engine.queues["G"].depth == 0
    assert engine.machines[0].status == MachineStatus.IDLE
    assert result == SimulationEngine(42, policy=policy).run_scenario(scenario)


@pytest.mark.parametrize("policy", [FIFOPolicy(), SPTPolicy(), CriticalRatioPolicy()])
def test_policy_handles_parallel_slots_and_reentrant_routes(policy):
    step = ProcessStep("S", "Station", 2, "G")
    scenario = SimulationScenario(
        "reentrant",
        42,
        (step,),
        (MachineConfig("M1", "G", 2), MachineConfig("M2", "G")),
        tuple(Lot(str(i), 0, 20, [step, step]) for i in range(6)),
    )
    engine = SimulationEngine(42, policy=policy)
    result = engine.run_scenario(scenario)
    active = {"M1": 0, "M2": 0}
    for event in result.events:
        if event.event_type == EventType.PROCESS_STARTED:
            active[event.machine_id] += 1
            assert active[event.machine_id] <= (2 if event.machine_id == "M1" else 1)
        elif event.event_type == EventType.PROCESS_COMPLETED:
            active[event.machine_id] -= 1
            assert active[event.machine_id] >= 0
    assert active == {"M1": 0, "M2": 0}
    assert result.finished_at == 8
    assert len(result.completed_lots) == 6
    assert all(lot.current_step == 2 for lot in result.completed_lots)
    assert engine.queues["G"].depth == 0
