"""Tests for the wafer-lot domain model."""

import pytest

from simulator.entities.lot import Lot, LotPriority


def test_create_valid_normal_lot() -> None:
    lot = Lot(
        lot_id="LOT-001",
        priority=LotPriority.NORMAL,
        arrival_time=0.0,
        due_date=120.0,
    )

    assert lot.lot_id == "LOT-001"
    assert lot.priority is LotPriority.NORMAL
    assert lot.arrival_time == 0.0
    assert lot.due_date == 120.0


def test_create_hot_lot() -> None:
    lot = Lot(
        lot_id="HOT-001",
        priority=LotPriority.HOT,
        arrival_time=10.0,
        due_date=60.0,
    )

    assert lot.priority is LotPriority.HOT


def test_reject_empty_lot_id() -> None:
    with pytest.raises(ValueError, match="lot_id must not be empty"):
        Lot(
            lot_id=" ",
            priority=LotPriority.NORMAL,
            arrival_time=0.0,
            due_date=120.0,
        )


def test_reject_negative_arrival_time() -> None:
    with pytest.raises(ValueError, match="arrival_time must be non-negative"):
        Lot(
            lot_id="LOT-001",
            priority=LotPriority.NORMAL,
            arrival_time=-1.0,
            due_date=120.0,
        )


def test_reject_due_date_before_arrival() -> None:
    with pytest.raises(
        ValueError,
        match="due_date must not be earlier than arrival_time",
    ):
        Lot(
            lot_id="LOT-001",
            priority=LotPriority.NORMAL,
            arrival_time=100.0,
            due_date=80.0,
        )
