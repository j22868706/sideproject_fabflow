"""Optional machine-wide outages; all durations are minutes."""

from dataclasses import dataclass
from math import isfinite


@dataclass(frozen=True)
class ReliabilityConfig:
    mtbf: float | None = None
    mttr: float | None = None
    outages: tuple[tuple[float, float], ...] = ()

    def __post_init__(self) -> None:
        if (self.mtbf is None) != (self.mttr is None):
            raise ValueError("mtbf and mttr must be supplied together")
        for value in (self.mtbf, self.mttr):
            if value is not None and (not isfinite(value) or value <= 0):
                raise ValueError("mtbf and mttr must be finite and positive")
        if self.mtbf is not None and self.outages:
            raise ValueError("choose random reliability or fixed outages")
        end = 0.0
        for start, duration in self.outages:
            if not isfinite(start) or not isfinite(duration) or start < end or duration <= 0:
                raise ValueError("outages must be finite, ordered, non-overlapping and positive")
            end = start + duration
