from dataclasses import replace

import pytest

from simulator.engine import SimulationEngine
from simulator.entities.lot import Lot, LotStatus
from simulator.entities.machine import MachineStatus
from simulator.entities.process_step import ProcessStep
from simulator.entities.scenario import MachineConfig, SimulationScenario
from simulator.events.event import EventType
from simulator.scenarios.baseline import create_baseline_scenario


def test_three_stage_hand_calculated_times_and_event_order() -> None:
    scenario = create_baseline_scenario()
    engine = SimulationEngine(scenario.seed)
    result = engine.run_scenario(scenario)
    assert [lot.completed_at for lot in result.completed_lots] == [23, 31, 39, 47, 55]
    assert result.average_cycle_time == 33
    assert result.throughput_per_hour == pytest.approx(5 * 60 / 55)
    for lot in result.completed_lots:
        assert lot.current_step == 3
        assert lot.status == LotStatus.COMPLETED
        events = [event for event in result.events if event.lot_id == lot.lot_id]
        assert [event.event_type for event in events] == [EventType.LOT_ARRIVED] + [
            EventType.LOT_QUEUED,
            EventType.PROCESS_STARTED,
            EventType.PROCESS_COMPLETED,
        ] * 3 + [EventType.LOT_COMPLETED]
        assert [
            event.step_id for event in events if event.event_type == EventType.PROCESS_STARTED
        ] == [step.step_id for step in lot.route]
        assert events[0].timestamp == lot.arrival_time
        starts = [event for event in events if event.event_type == EventType.PROCESS_STARTED]
        assert lot.started_at == starts[0].timestamp
    assert all(queue.depth == 0 for queue in engine.queues.values())
    assert all(machine.status == MachineStatus.IDLE for machine in engine.machines)


def test_capacity_and_machine_eligibility_at_every_event() -> None:
    scenario = create_baseline_scenario(number_of_lots=20)
    scenario = replace(scenario, machines=tuple(replace(m, capacity=2) for m in scenario.machines))
    engine = SimulationEngine(scenario.seed)
    result = engine.run_scenario(scenario)
    machines = {machine.machine_id: machine for machine in engine.machines}
    steps = {step.step_id: step for step in scenario.process_steps}
    counts = dict.fromkeys(machines, 0)
    peaks = dict.fromkeys(machines, 0)
    for event in result.events:
        if event.event_type == EventType.PROCESS_STARTED:
            machine = machines[event.machine_id]
            assert machine.group == steps[event.step_id].eligible_machine_group
            counts[event.machine_id] += 1
            peaks[event.machine_id] = max(peaks[event.machine_id], counts[event.machine_id])
            assert counts[event.machine_id] <= machine.capacity
        elif event.event_type == EventType.PROCESS_COMPLETED:
            counts[event.machine_id] -= 1
            assert counts[event.machine_id] >= 0
    assert all(value == 0 for value in counts.values())
    assert max(peaks.values()) == 2
    assert len(result.completed_lots) == 20
    assert sum(machine.busy_time for machine in engine.machines) == 20 * 23


def test_same_scenario_repeats_without_mutating_inputs() -> None:
    scenario = create_baseline_scenario()
    first = SimulationEngine(scenario.seed).run_scenario(scenario)
    second = SimulationEngine(scenario.seed).run_scenario(scenario)
    assert first == second
    assert all(
        lot.status == LotStatus.CREATED and lot.completed_at is None for lot in scenario.lots
    )
    assert first.completed_lots[0] is not second.completed_lots[0]


def test_busy_state_remains_busy_until_all_capacity_slots_finish() -> None:
    step = ProcessStep("S", "Station", 4, "G")
    scenario = SimulationScenario(
        "capacity",
        42,
        (step,),
        (MachineConfig("M", "G", 2),),
        (Lot("A", 0, 20, [step]), Lot("B", 1, 20, [step]), Lot("C", 2, 20, [step])),
    )
    engine = SimulationEngine(42)

    def observe():
        yield engine.env.timeout(4.5)
        machine = engine.machines[0]
        assert machine.status == MachineStatus.BUSY
        assert {lot.lot_id for lot in machine.active_lots} == {"B", "C"}
        assert engine.queues["G"].depth == 0

    engine.env.process(observe())
    result = engine.run_scenario(scenario)
    assert [lot.completed_at for lot in result.completed_lots] == [4, 5, 8]
    assert engine.machines[0].active_lots == []


def test_engine_rejects_reuse_and_seed_mismatch() -> None:
    scenario = create_baseline_scenario()
    with pytest.raises(ValueError, match="seed"):
        SimulationEngine(1).run_scenario(scenario)
    engine = SimulationEngine(42)
    engine.run_scenario(scenario)
    with pytest.raises(ValueError, match="fresh engine"):
        engine.run_scenario(scenario)


def test_hot_lot_precedes_normal_at_same_arrival_time() -> None:
    from simulator.entities.lot import LotPriority

    step = ProcessStep("S", "Station", 4, "G")
    scenario = SimulationScenario(
        "fifo",
        42,
        (step,),
        (MachineConfig("M", "G"),),
        (Lot("Z", 0, 20, [step]), Lot("A", 0, 20, [step], LotPriority.HOT)),
    )
    result = SimulationEngine(42).run_scenario(scenario)
    assert [lot.lot_id for lot in result.completed_lots] == ["A", "Z"]
    assert [lot.completed_at for lot in result.completed_lots] == [4, 8]


def test_documented_single_station_baseline() -> None:
    from simulator.entities.machine import Machine
    from simulator.entities.queue import Queue

    engine = SimulationEngine(42)
    lots = [
        Lot(f"LOT-{i:03d}", arrival, due, [ProcessStep(f"S{i}", "Station", duration, "G")])
        for i, (arrival, duration, due) in enumerate([(0, 10, 20), (2, 5, 20), (4, 8, 30)], 1)
    ]
    result = engine.run(lots, Machine(engine.env, "M", "G"), Queue("Q"))
    assert [lot.started_at for lot in result.completed_lots] == [0, 10, 15]
    assert [lot.completed_at for lot in result.completed_lots] == [10, 15, 23]
    assert result.average_cycle_time == 14
    assert result.throughput_per_hour == pytest.approx(3 * 60 / 23)
