from dataclasses import dataclass


@dataclass(frozen=True)
class ProcessStep:
    """A single manufacturing step in a wafer lot route."""

    step_id: str
    name: str
    processing_time: float
    eligible_machine_group: str

    def __post_init__(self) -> None:
        if not self.step_id:
            raise ValueError("step_id must not be empty")

        if not self.name:
            raise ValueError("name must not be empty")

        if self.processing_time <= 0:
            raise ValueError("processing_time must be greater than zero")

        if not self.eligible_machine_group:
            raise ValueError("eligible_machine_group must not be empty")
