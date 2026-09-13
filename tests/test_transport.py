from dataclasses import replace

import pytest

from app.simulation.amhs import compare_vehicles, main
from simulator.engine import SimulationEngine
from simulator.entities.lot import Lot, LotStatus
from simulator.entities.process_step import ProcessStep
from simulator.entities.reliability import ReliabilityConfig
from simulator.entities.scenario import MachineConfig, SimulationScenario
from simulator.entities.transport import TransportConfig
from simulator.events.event import EventType
from simulator.scenarios.amhs import create_amhs_scenario
from simulator.scenarios.baseline import create_baseline_scenario


def small_scenario() -> SimulationScenario:
    steps = (ProcessStep("A", "A", 1, "A"), ProcessStep("B", "B", 1, "B"))
    return SimulationScenario(
        "transport",
        42,
        steps,
        (MachineConfig("A", "A"), MachineConfig("B", "B")),
        (Lot("1", 0, 20, list(steps)), Lot("2", 0, 20, list(steps))),
        TransportConfig(1, 3),
    )


def test_hand_calculated_transport_and_manufacturing_kpis() -> None:
    engine = SimulationEngine(42)
    result = engine.run_scenario(small_scenario())
    assert [(j.requested_time, j.pickup_time, j.delivery_time) for j in result.transport_jobs] == [
        (1, 1, 4),
        (2, 4, 7),
    ]
    assert [(j.origin, j.destination) for j in result.transport_jobs] == [("A", "B")] * 2
    assert [lot.completed_at for lot in result.completed_lots] == [5, 8]
    k = result.kpis
    assert k.average_transport_time == 3
    assert k.average_transport_waiting_time == 1
    assert k.vehicle_utilization == 0.75
    assert k.transport_job_count == 2
    assert k.average_cycle_time == 6.5
    assert k.average_wip == 13 / 8
    assert k.average_waiting_time == 0.5  # Station wait excludes transport wait.
    assert all(m.busy_time == 2 for m in result.machines)
    assert engine.vehicles.count == 0
    assert not engine.vehicles.queue
    assert all(q.depth == 0 for q in engine.queues.values())
    for lot in result.completed_lots:
        events = [e for e in result.events if e.lot_id == lot.lot_id]
        assert [e.event_type for e in events] == [
            EventType.LOT_ARRIVED,
            EventType.LOT_QUEUED,
            EventType.PROCESS_STARTED,
            EventType.PROCESS_COMPLETED,
            EventType.TRANSPORT_REQUESTED,
            EventType.TRANSPORT_STARTED,
            EventType.TRANSPORT_COMPLETED,
            EventType.LOT_QUEUED,
            EventType.PROCESS_STARTED,
            EventType.PROCESS_COMPLETED,
            EventType.LOT_COMPLETED,
        ]
        assert events[6].timestamp == events[7].timestamp
        assert len({e.transport_job_id for e in events[4:7]}) == 1


@pytest.mark.parametrize("count", [1, 3])
def test_capacity_fifo_reproducibility_and_input_isolation(count: int) -> None:
    scenario = create_amhs_scenario(count)
    first = SimulationEngine(42).run_scenario(scenario)
    assert first == SimulationEngine(42).run_scenario(scenario)
    active = peak = 0
    requested, started = [], []
    for e in first.events:
        if e.event_type == EventType.TRANSPORT_REQUESTED:
            requested.append(e.transport_job_id)
        elif e.event_type == EventType.TRANSPORT_STARTED:
            started.append(e.transport_job_id)
            active += 1
            peak = max(peak, active)
        elif e.event_type == EventType.TRANSPORT_COMPLETED:
            active -= 1
        assert 0 <= active <= count
    assert active == 0 and peak == count
    assert requested == started
    assert len(first.transport_jobs) == 40
    assert all(lot.status == LotStatus.CREATED for lot in scenario.lots)


def test_vehicle_congestion_and_processing_bottleneck() -> None:
    one, three, six = [row["kpis"] for row in compare_vehicles()]
    assert one["average_transport_waiting_time"] > three["average_transport_waiting_time"] > 0
    assert one["average_cycle_time"] > three["average_cycle_time"]
    assert one["throughput_per_hour"] < three["throughput_per_hour"]
    assert three["throughput_per_hour"] == six["throughput_per_hour"]
    assert six["average_transport_waiting_time"] == 0
    assert one["machines"][1]["utilization"] < three["machines"][1]["utilization"]
    assert three["machines"][1]["utilization"] == max(m["utilization"] for m in three["machines"])


@pytest.mark.parametrize("count", [0, -1, 1.5, True])
def test_invalid_vehicle_count(count: int) -> None:
    with pytest.raises(ValueError, match="vehicle_count"):
        TransportConfig(count)


@pytest.mark.parametrize("duration", [-1, float("inf"), float("nan")])
def test_invalid_travel_time(duration: float) -> None:
    with pytest.raises(ValueError, match="travel_time"):
        TransportConfig(travel_time=duration)


def test_disabled_zero_time_and_single_step_transport() -> None:
    scenario = create_baseline_scenario()
    disabled = SimulationEngine(42).run_scenario(scenario)
    zero = SimulationEngine(42).run_scenario(replace(scenario, transport=TransportConfig(1, 0)))
    assert [lot.completed_at for lot in disabled.completed_lots] == [
        lot.completed_at for lot in zero.completed_lots
    ]
    assert disabled.kpis.transport_job_count == disabled.kpis.vehicle_utilization == 0
    assert zero.kpis.transport_job_count == 10
    assert zero.kpis.vehicle_utilization == 0
    single = replace(small_scenario(), lots=(Lot("1", 0, 20, [small_scenario().process_steps[0]]),))
    assert SimulationEngine(42).run_scenario(single).transport_jobs == ()


def test_repeated_station_visit_and_downstream_failure() -> None:
    scenario = small_scenario()
    a, b = scenario.process_steps
    scenario = replace(
        scenario,
        lots=(Lot("1", 0, 30, [a, b, a]),),
        machines=(
            scenario.machines[0],
            replace(scenario.machines[1], reliability=ReliabilityConfig(outages=((3, 3),))),
        ),
    )
    result = SimulationEngine(42).run_scenario(scenario)
    assert [(j.origin, j.destination) for j in result.transport_jobs] == [("A", "B"), ("B", "A")]
    assert result.completed_lots[0].completed_at == 11
    assert result.kpis.average_waiting_time == 2


def test_report_and_json_export(tmp_path, monkeypatch) -> None:
    import json

    report, export = tmp_path / "report.md", tmp_path / "result.json"
    monkeypatch.setattr("sys.argv", ["amhs", "--output", str(report), "--json", str(export)])
    main()
    rows = json.loads(export.read_text())
    assert [row["vehicle_count"] for row in rows] == [1, 3, 6]
    assert len(rows[0]["transport_jobs"]) == 40
    assert "5.91" in report.read_text()


def test_transport_shortage_leaves_downstream_waiting_for_delivery() -> None:
    idle_times = []
    for count in (1, 3):
        result = SimulationEngine(42).run_scenario(create_amhs_scenario(count))
        starts = [
            e
            for e in result.events
            if e.machine_id == "ETCH-01" and e.event_type == EventType.PROCESS_STARTED
        ]
        ends = [
            e
            for e in result.events
            if e.machine_id == "ETCH-01" and e.event_type == EventType.PROCESS_COMPLETED
        ]
        idle = 0.0
        for end, start in zip(ends, starts[1:], strict=False):
            gap = start.timestamp - end.timestamp
            assert gap >= 0
            idle += gap
            if gap:
                # No lot is queued at Etching throughout this idle interval.
                assert not any(
                    e.event_type == EventType.LOT_QUEUED
                    and e.step_id == "E"
                    and end.timestamp <= e.timestamp < start.timestamp
                    for e in result.events
                )
                # Service resumes exactly when the next delivery reaches the station.
                assert any(
                    e.event_type == EventType.TRANSPORT_COMPLETED
                    and e.destination == "ETCH"
                    and e.lot_id == start.lot_id
                    and e.timestamp == start.timestamp
                    for e in result.events
                )
        idle_times.append(idle)
    assert idle_times == [44, 0]
