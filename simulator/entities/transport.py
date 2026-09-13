"""Simplified AMHS inputs and completed transport records; times are minutes."""

from dataclasses import dataclass
from math import isfinite


@dataclass(frozen=True)
class TransportConfig:
    vehicle_count: int = 1
    travel_time: float = 5.0

    def __post_init__(self) -> None:
        if (
            isinstance(self.vehicle_count, bool)
            or not isinstance(self.vehicle_count, int)
            or self.vehicle_count <= 0
        ):
            raise ValueError("vehicle_count must be a positive integer")
        if not isfinite(self.travel_time) or self.travel_time < 0:
            raise ValueError("travel_time must be finite and non-negative")


@dataclass(frozen=True)
class TransportJob:
    job_id: str
    lot_id: str
    origin: str
    destination: str
    requested_time: float
    pickup_time: float
    delivery_time: float

    @property
    def waiting_time(self) -> float:
        return self.pickup_time - self.requested_time

    @property
    def transport_time(self) -> float:
        return self.delivery_time - self.pickup_time
