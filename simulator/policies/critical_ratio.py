from collections.abc import Sequence

from simulator.policies.base import DispatchCandidate


class CriticalRatioPolicy:
    """Select the lowest time-to-due / remaining-processing-time ratio."""

    def select(
        self, candidates: Sequence[DispatchCandidate], current_time: float
    ) -> DispatchCandidate:
        if not candidates:
            raise ValueError("cannot dispatch from an empty queue")

        def rank(candidate: DispatchCandidate) -> tuple[float, float, int]:
            lot = candidate.lot
            remaining = sum(step.processing_time for step in lot.route[lot.current_step :])
            if remaining <= 0:
                raise ValueError("candidate must have remaining processing time")
            return (
                (lot.due_date - current_time) / remaining,
                candidate.queued_at,
                candidate.sequence,
            )

        return min(candidates, key=rank)
