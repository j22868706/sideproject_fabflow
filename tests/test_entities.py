import pytest

from simulator.entities.lot import Lot
from simulator.entities.process_step import ProcessStep
from simulator.entities.queue import Queue


def create_process_step() -> ProcessStep:
    return ProcessStep(
        step_id="STEP-001",
        name="Lithography",
        processing_time=4.0,
        eligible_machine_group="LITHO",
    )


def create_lot(lot_id: str = "LOT-001") -> Lot:
    return Lot(
        lot_id=lot_id,
        arrival_time=0.0,
        due_date=20.0,
        route=[create_process_step()],
    )


def test_process_step_rejects_non_positive_processing_time() -> None:
    with pytest.raises(
        ValueError,
        match="processing_time must be greater than zero",
    ):
        ProcessStep(
            step_id="STEP-001",
            name="Lithography",
            processing_time=0,
            eligible_machine_group="LITHO",
        )


def test_lot_rejects_due_date_before_arrival() -> None:
    with pytest.raises(
        ValueError,
        match="due_date must not be earlier than arrival_time",
    ):
        Lot(
            lot_id="LOT-001",
            arrival_time=10.0,
            due_date=5.0,
            route=[create_process_step()],
        )


def test_queue_tracks_waiting_lots() -> None:
    queue = Queue(queue_id="QUEUE-LITHO")
    lot = create_lot()

    queue.enqueue(lot)

    assert queue.depth == 1
    assert queue.waiting_lots == [lot]

    queue.dequeue(lot)

    assert queue.depth == 0
    assert queue.waiting_lots == []
