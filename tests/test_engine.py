from simulator.engine import SimulationEngine
from simulator.entities.lot import Lot, LotStatus
from simulator.entities.machine import Machine
from simulator.entities.process_step import ProcessStep
from simulator.entities.queue import Queue
from simulator.events.event import EventType


def create_baseline_lots() -> list[Lot]:
    process_step = ProcessStep(
        step_id="STEP-001",
        name="Lithography",
        processing_time=4.0,
        eligible_machine_group="LITHO",
    )

    return [
        Lot(
            lot_id="LOT-001",
            arrival_time=0.0,
            due_date=20.0,
            route=[process_step],
        ),
        Lot(
            lot_id="LOT-002",
            arrival_time=1.0,
            due_date=20.0,
            route=[process_step],
        ),
        Lot(
            lot_id="LOT-003",
            arrival_time=2.0,
            due_date=20.0,
            route=[process_step],
        ),
    ]


def run_baseline(seed: int = 42):
    engine = SimulationEngine(seed=seed)

    machine = Machine(
        env=engine.env,
        machine_id="MACHINE-001",
        group="LITHO",
        capacity=1,
    )

    queue = Queue(queue_id="QUEUE-LITHO")

    result = engine.run(
        lots=create_baseline_lots(),
        machine=machine,
        queue=queue,
    )

    return result, machine, queue


def test_baseline_completion_times() -> None:
    result, machine, queue = run_baseline()

    completion_times = {lot.lot_id: lot.completed_at for lot in result.completed_lots}

    assert completion_times == {
        "LOT-001": 4.0,
        "LOT-002": 8.0,
        "LOT-003": 12.0,
    }

    assert result.finished_at == 12.0
    assert machine.busy_time == 12.0
    assert queue.depth == 0


def test_every_lot_is_completed_once() -> None:
    result, _, _ = run_baseline()

    completed_ids = [lot.lot_id for lot in result.completed_lots]

    assert completed_ids == [
        "LOT-001",
        "LOT-002",
        "LOT-003",
    ]

    assert len(completed_ids) == len(set(completed_ids))

    assert all(lot.status == LotStatus.COMPLETED for lot in result.completed_lots)


def test_event_log_contains_expected_event_counts() -> None:
    result, _, _ = run_baseline()

    event_types = [event.event_type for event in result.events]

    assert event_types.count(EventType.LOT_ARRIVED) == 3
    assert event_types.count(EventType.LOT_QUEUED) == 3
    assert event_types.count(EventType.PROCESS_STARTED) == 3
    assert event_types.count(EventType.PROCESS_COMPLETED) == 3
    assert event_types.count(EventType.LOT_COMPLETED) == 3

    assert len(result.events) == 15


def test_same_seed_produces_same_event_log() -> None:
    first_result, _, _ = run_baseline(seed=42)
    second_result, _, _ = run_baseline(seed=42)

    assert first_result.events == second_result.events
