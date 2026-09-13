import pytest

from simulator.engine import SimulationEngine, SimulationResult
from simulator.entities.lot import Lot
from simulator.entities.process_step import ProcessStep
from simulator.entities.reliability import ReliabilityConfig
from simulator.entities.scenario import MachineConfig, SimulationScenario


def test_hand_calculated_kpis_with_queueing_and_failure():
    step = ProcessStep("S", "Station", 4, "G")
    scenario = SimulationScenario(
        "kpi",
        42,
        (step,),
        (MachineConfig("M", "G", reliability=ReliabilityConfig(outages=((2, 2),))),),
        (Lot("A", 0, 6, [step]), Lot("B", 1, 8, [step])),
    )
    kpi = SimulationEngine(42).run_scenario(scenario).kpis
    # A: 0..6, B: 6..10; cycle times 6, 9; queue waits 0, 5.
    assert kpi.observation_minutes == 10
    assert kpi.completed_lots == 2
    assert kpi.average_cycle_time == 7.5
    assert kpi.p95_cycle_time == 9
    assert kpi.throughput_per_hour == 12
    assert kpi.average_wip == 1.5
    assert kpi.average_waiting_time == 2.5
    assert kpi.average_queue_depth == 0.5
    assert kpi.max_queue_depth == 1
    assert kpi.on_time_delivery_rate == 0.5
    assert kpi.average_tardiness == 1
    assert kpi.machines[0].utilization == pytest.approx(0.8)
    assert kpi.machines[0].availability == pytest.approx(0.8)
    assert kpi.machines[0].downtime == 2


def test_empty_result_kpis_are_defined():
    kpi = SimulationResult(0, (), ()).kpis
    assert kpi.completed_lots == 0
    assert kpi.average_cycle_time == kpi.p95_cycle_time == kpi.average_wip == 0
    assert kpi.throughput_per_hour == kpi.on_time_delivery_rate == 0
    assert kpi.machines == ()
