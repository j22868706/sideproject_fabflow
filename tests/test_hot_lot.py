from dataclasses import replace

import pytest

from simulator.engine import SimulationEngine
from simulator.entities.lot import Lot, LotPriority
from simulator.entities.process_step import ProcessStep
from simulator.entities.scenario import MachineConfig, SimulationScenario
from simulator.events.event import EventType
from simulator.policies.base import DispatchCandidate
from simulator.policies.critical_ratio import CriticalRatioPolicy
from simulator.policies.fifo import FIFOPolicy
from simulator.policies.hot_lot import HotLotPolicy
from simulator.policies.spt import SPTPolicy


def candidate(name, priority=LotPriority.NORMAL, queued_at=0, duration=2, due=100, sequence=0):
    step = ProcessStep(name, "Station", duration, "G")
    return DispatchCandidate(Lot(name, 0, due, [step], priority), queued_at, sequence)


@pytest.mark.parametrize("base", [FIFOPolicy(), SPTPolicy(), CriticalRatioPolicy()])
def test_hot_overrides_base_ranking_without_mutating_queue(base):
    normal = candidate("normal", duration=1, due=1)
    hot = candidate("hot", LotPriority.HOT, queued_at=2, duration=10)
    candidates = [normal, hot]
    assert HotLotPolicy(base).select(candidates, 3) is hot
    assert candidates == [normal, hot]
    assert normal.lot.priority == LotPriority.NORMAL
    with pytest.raises(ValueError, match="empty queue"):
        HotLotPolicy(base).select([], 3)


@pytest.mark.parametrize(
    ("base", "expected"),
    [
        (FIFOPolicy(), "first"),
        (SPTPolicy(), "short"),
        (CriticalRatioPolicy(), "urgent"),
    ],
)
@pytest.mark.parametrize("priority", [LotPriority.NORMAL, LotPriority.HOT])
def test_base_policy_ranks_within_priority_class(base, expected, priority):
    candidates = [
        candidate("first", priority, duration=6, sequence=0),
        candidate("short", priority, duration=2, sequence=1),
        candidate("urgent", priority, duration=4, due=5, sequence=2),
    ]
    assert HotLotPolicy(base).select(candidates, 3).lot.lot_id == expected


def test_aging_uses_station_entry_time_and_inclusive_threshold():
    normal = candidate("normal", queued_at=20)
    hot = candidate("hot", LotPriority.HOT, queued_at=24)
    policy = HotLotPolicy(SPTPolicy(), normal_wait_threshold=5)
    assert policy.select([normal, hot], 24.999) is hot
    assert policy.select([normal, hot], 25) is normal
    # Arrival time stays zero; entering a new station resets the aging clock.
    requeued = replace(normal, queued_at=25)
    assert policy.select([requeued, hot], 26) is hot


def test_aged_normals_use_fifo_even_when_spt_prefers_newer_short_lot():
    oldest = candidate("old", duration=20, sequence=0)
    tied = candidate("tied", duration=1, sequence=1)
    newer = candidate("newer", queued_at=1, duration=1)
    hot = candidate("hot", LotPriority.HOT)
    policy = HotLotPolicy(SPTPolicy(), normal_wait_threshold=5)
    assert policy.select([hot, newer, tied, oldest], 10) is oldest


@pytest.mark.parametrize("base", [FIFOPolicy(), SPTPolicy(), CriticalRatioPolicy()])
def test_normal_is_dispatched_before_hot_stream_ends(base):
    step = ProcessStep("S", "Station", 2, "G")
    lots = (
        Lot("blocker", 0, 100, [step]),
        Lot("normal", 1, 100, [step]),
        *(Lot(f"hot-{i}", i + 1.5, 100, [step], LotPriority.HOT) for i in range(10)),
    )
    scenario = SimulationScenario("hot-stream", 42, (step,), (MachineConfig("M", "G"),), lots)
    engine = SimulationEngine(42, base, normal_wait_threshold=5)
    result = engine.run_scenario(scenario)
    starts = [e for e in result.events if e.event_type == EventType.PROCESS_STARTED]
    assert [(e.lot_id, e.timestamp) for e in starts[:4]] == [
        ("blocker", 0),
        ("hot-0", 2),
        ("hot-1", 4),
        ("normal", 6),
    ]
    # The initial operation is not preempted; normal is served while new hot lots still arrive.
    assert result.completed_lots[0].completed_at == 2
    assert starts[3].queue_depth > 0
    assert len(result.completed_lots) == 12
    assert engine.queues["G"].depth == 0
    assert result == SimulationEngine(42, base, normal_wait_threshold=5).run_scenario(scenario)
    assert all(lot.completed_at is None for lot in scenario.lots)


@pytest.mark.parametrize("threshold", [0, -1, float("nan"), float("inf")])
def test_engine_rejects_invalid_aging_threshold(threshold):
    with pytest.raises(ValueError, match="finite and positive"):
        SimulationEngine(42, normal_wait_threshold=threshold)
