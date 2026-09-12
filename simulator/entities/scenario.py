from dataclasses import dataclass

from simulator.entities.lot import Lot
from simulator.entities.process_step import ProcessStep


@dataclass(frozen=True)
class MachineConfig:
    """Machine settings before creating SimPy runtime resources."""

    machine_id: str
    group: str
    capacity: int = 1

    def __post_init__(self) -> None:
        if not self.machine_id.strip():
            raise ValueError("machine_id must not be empty")
        if not self.group.strip():
            raise ValueError("group must not be empty")
        if self.capacity <= 0:
            raise ValueError("capacity must be greater than zero")


@dataclass(frozen=True)
class SimulationScenario:
    """Inputs for a simulation experiment."""

    scenario_id: str
    seed: int
    process_steps: tuple[ProcessStep, ...]
    machines: tuple[MachineConfig, ...]
    lots: tuple[Lot, ...]

    def __post_init__(self) -> None:
        if not self.scenario_id.strip():
            raise ValueError("scenario_id must not be empty")

        if not self.process_steps:
            raise ValueError("scenario must contain process steps")
        if not self.machines:
            raise ValueError("scenario must contain machines")
        if not self.lots:
            raise ValueError("scenario must contain lots")

        step_ids = [step.step_id for step in self.process_steps]
        machine_ids = [machine.machine_id for machine in self.machines]
        lot_ids = [lot.lot_id for lot in self.lots]

        if len(step_ids) != len(set(step_ids)):
            raise ValueError("step_id must be unique")
        if len(machine_ids) != len(set(machine_ids)):
            raise ValueError("machine_id must be unique")
        if len(lot_ids) != len(set(lot_ids)):
            raise ValueError("lot_id must be unique")

        available_groups = {machine.group for machine in self.machines}

        for step in self.process_steps:
            if step.eligible_machine_group not in available_groups:
                raise ValueError(f"no machine available for process step {step.step_id}")

        defined_steps = {step.step_id: step for step in self.process_steps}

        for lot in self.lots:
            if not lot.route:
                raise ValueError(f"lot {lot.lot_id} must have a route")

            for step in lot.route:
                if defined_steps.get(step.step_id) != step:
                    raise ValueError(f"lot {lot.lot_id} references an undefined process step")
