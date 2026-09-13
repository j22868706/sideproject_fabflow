"""Hot-lot insertion with a simple station waiting-time safeguard."""

from collections.abc import Sequence
from math import isfinite

from simulator.entities.lot import LotPriority
from simulator.policies.base import DispatchCandidate, DispatchPolicy
from simulator.policies.fifo import FIFOPolicy


class HotLotPolicy:
    """Dispatch aged Normal lots FIFO, then Hot lots, then other Normal lots."""

    def __init__(self, policy: DispatchPolicy, normal_wait_threshold: float = 60.0) -> None:
        if not isfinite(normal_wait_threshold) or normal_wait_threshold <= 0:
            raise ValueError("normal_wait_threshold must be finite and positive")
        self.policy = policy
        self.normal_wait_threshold = normal_wait_threshold

    def select(
        self, candidates: Sequence[DispatchCandidate], current_time: float
    ) -> DispatchCandidate:
        aged = tuple(
            candidate
            for candidate in candidates
            if candidate.lot.priority == LotPriority.NORMAL
            and current_time - candidate.queued_at >= self.normal_wait_threshold
        )
        if aged:
            # Oldest first prevents SPT/CR from repeatedly bypassing an aged lot.
            return FIFOPolicy().select(aged, current_time)
        hot = tuple(
            candidate for candidate in candidates if candidate.lot.priority == LotPriority.HOT
        )
        return self.policy.select(hot or candidates, current_time)
