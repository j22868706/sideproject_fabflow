from dataclasses import replace

import pytest

from simulator.engine import SimulationEngine
from simulator.entities.lot import Lot
from simulator.entities.machine import MachineStatus
from simulator.entities.process_step import ProcessStep
from simulator.entities.reliability import ReliabilityConfig
from simulator.entities.scenario import MachineConfig, SimulationScenario
from simulator.events.event import EventType
from simulator.policies.spt import SPTPolicy


def scenario(reliability, capacity=1, arrivals=(0, 1), duration=10):
    step = ProcessStep("S", "Station", duration, "G")
    return SimulationScenario(
        "reliability",
        42,
        (step,),
        (MachineConfig("M", "G", capacity, reliability),),
        tuple(Lot(str(i), arrival, 100, [step]) for i, arrival in enumerate(arrivals)),
    )


def test_failure_pauses_work_and_prevents_dispatch_until_repaired():
    engine = SimulationEngine(42)
    result = engine.run_scenario(scenario(ReliabilityConfig(outages=((3, 4), (9, 2)))))
    assert [lot.completed_at for lot in result.completed_lots] == [16, 26]
    assert [lot.started_at for lot in result.completed_lots] == [0, 16]
    assert engine.machines[0].busy_time == 20
    assert engine.machines[0].downtime == 6
    assert engine.machines[0].status == MachineStatus.IDLE
    assert engine.queues["G"].depth == 0
    failures = [e for e in result.events if e.event_type == EventType.MACHINE_FAILED]
    assert [(e.timestamp, e.lot_id, e.machine_id) for e in failures] == [
        (3, None, "M"),
        (9, None, "M"),
    ]


def test_failure_pauses_all_capacity_slots():
    result = SimulationEngine(42).run_scenario(
        scenario(ReliabilityConfig(outages=((3, 4),)), capacity=2, arrivals=(0, 1, 2))
    )
    assert [lot.completed_at for lot in result.completed_lots] == [14, 15, 24]
    assert result.kpis.machines[0].utilization == pytest.approx(30 / 48)


def test_idle_failure_blocks_start_and_future_failures_do_not_extend_run():
    result = SimulationEngine(42).run_scenario(
        scenario(ReliabilityConfig(outages=((0, 5), (100, 10))), arrivals=(1,), duration=2)
    )
    assert result.completed_lots[0].started_at == 5
    assert result.finished_at == 7
    assert result.kpis.average_waiting_time == 4


def test_healthy_machine_can_dispatch_while_peer_is_down():
    config = scenario(ReliabilityConfig(outages=((0, 50),)), arrivals=(1,), duration=2)
    config = replace(config, machines=config.machines + (MachineConfig("healthy", "G"),))
    result = SimulationEngine(42).run_scenario(config)
    assert result.finished_at == 3
    assert result.kpis.machines[0].downtime == 3
    assert result.kpis.machines[0].availability == 0
    assert not any(e.event_type == EventType.MACHINE_REPAIRED for e in result.events)


def test_random_failures_repeat_and_share_calendar_across_policies():
    config = scenario(ReliabilityConfig(mtbf=3, mttr=1), arrivals=(0, 1, 2, 3))
    first = SimulationEngine(42).run_scenario(config)
    assert first == SimulationEngine(42).run_scenario(config)
    second = SimulationEngine(42, SPTPolicy()).run_scenario(config)

    def failures(result):
        return [e for e in result.events if e.lot_id is None]

    assert failures(first)
    assert failures(first) == failures(second)
    assert all(lot.completed_at is None for lot in config.lots)
    assert first != SimulationEngine(43).run_scenario(replace(config, seed=43))


@pytest.mark.parametrize(
    "kwargs",
    [
        {"mtbf": 1},
        {"mtbf": 0, "mttr": 1},
        {"mtbf": float("nan"), "mttr": 1},
        {"outages": ((-1, 2),)},
        {"outages": ((0, 0),)},
        {"outages": ((1, 3), (2, 1))},
        {"mtbf": 1, "mttr": 1, "outages": ((0, 1),)},
    ],
)
def test_invalid_reliability_rejected(kwargs):
    with pytest.raises(ValueError):
        ReliabilityConfig(**kwargs)
