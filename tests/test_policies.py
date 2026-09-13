import pytest

from simulator.entities.lot import Lot
from simulator.entities.process_step import ProcessStep
from simulator.policies.base import DispatchCandidate
from simulator.policies.fifo import FIFOPolicy


def make_candidate(
    lot_id: str,
    arrival_time: float,
    queued_at: float,
    sequence: int,
) -> DispatchCandidate:
    step = ProcessStep(
        step_id="ETCH",
        name="Etching",
        processing_time=5.0,
        eligible_machine_group="ETCH",
    )
    lot = Lot(
        lot_id=lot_id,
        arrival_time=arrival_time,
        due_date=100.0,
        route=[step],
    )
    return DispatchCandidate(
        lot=lot,
        queued_at=queued_at,
        sequence=sequence,
    )


def test_fifo_uses_station_queue_time_instead_of_fab_arrival() -> None:
    earlier_fab_arrival = make_candidate(
        lot_id="A",
        arrival_time=0.0,
        queued_at=12.0,
        sequence=1,
    )
    earlier_queue_entry = make_candidate(
        lot_id="B",
        arrival_time=2.0,
        queued_at=10.0,
        sequence=0,
    )

    selected = FIFOPolicy().select(
        [earlier_fab_arrival, earlier_queue_entry],
        current_time=15.0,
    )

    assert selected is earlier_queue_entry


def test_fifo_breaks_queue_time_ties_by_sequence() -> None:
    first = make_candidate("Z", 0.0, 10.0, 0)
    second = make_candidate("A", 0.0, 10.0, 1)

    selected = FIFOPolicy().select(
        [second, first],
        current_time=10.0,
    )

    assert selected is first


def test_fifo_does_not_modify_candidates() -> None:
    first = make_candidate("A", 0.0, 1.0, 0)
    second = make_candidate("B", 0.0, 2.0, 1)
    candidates = [second, first]

    FIFOPolicy().select(candidates, current_time=3.0)

    assert candidates == [second, first]


def test_fifo_rejects_empty_queue() -> None:
    with pytest.raises(ValueError, match="empty queue"):
        FIFOPolicy().select([], current_time=0.0)
