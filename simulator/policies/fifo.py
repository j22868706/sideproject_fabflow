from collections.abc import Sequence

from simulator.policies.base import DispatchCandidate


class FIFOPolicy:
    """Select the candidate that entered the station queue first."""

    def select(
        self,
        candidates: Sequence[DispatchCandidate],
        current_time: float,
    ) -> DispatchCandidate:
        if not candidates:
            raise ValueError("cannot dispatch from an empty queue")

        return min(
            candidates,
            key=lambda candidate: (
                candidate.queued_at,
                candidate.sequence,
            ),
        )
