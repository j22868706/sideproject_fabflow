from dataclasses import dataclass, field

from simulator.entities.lot import Lot


@dataclass
class Queue:
    """A FIFO waiting queue for wafer lots."""

    queue_id: str
    waiting_lots: list[Lot] = field(default_factory=list)

    def enqueue(self, lot: Lot) -> None:
        if lot in self.waiting_lots:
            raise ValueError(f"lot {lot.lot_id} is already in the queue")

        self.waiting_lots.append(lot)

    def dequeue(self, lot: Lot) -> None:
        if lot not in self.waiting_lots:
            raise ValueError(f"lot {lot.lot_id} is not in the queue")

        self.waiting_lots.remove(lot)

    @property
    def depth(self) -> int:
        return len(self.waiting_lots)
