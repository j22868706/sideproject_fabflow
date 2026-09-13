from collections.abc import Sequence

from simulator.policies.base import DispatchCandidate


class SPTPolicy:
    """Select the shortest current operation, breaking ties by station FIFO."""

    def select(
        self, candidates: Sequence[DispatchCandidate], current_time: float
    ) -> DispatchCandidate:
        if not candidates:
            raise ValueError("cannot dispatch from an empty queue")
        return min(
            candidates,
            key=lambda candidate: (
                candidate.lot.current_process_step.processing_time,
                candidate.queued_at,
                candidate.sequence,
            ),
        )
