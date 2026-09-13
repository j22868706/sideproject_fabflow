"""Paired experiments that move the bottleneck from AMHS to Etching."""

from simulator.entities.lot import Lot
from simulator.entities.process_step import ProcessStep
from simulator.entities.scenario import MachineConfig, SimulationScenario
from simulator.entities.transport import TransportConfig


def create_amhs_scenario(vehicle_count: int = 1, *, seed: int = 42) -> SimulationScenario:
    steps = (
        ProcessStep("L", "Lithography", 2, "LITHO"),
        ProcessStep("E", "Etching", 4, "ETCH"),
        ProcessStep("I", "Inspection", 1, "INSPECT"),
    )
    return SimulationScenario(
        scenario_id="amhs-bottleneck",
        seed=seed,
        process_steps=steps,
        machines=tuple(
            MachineConfig(f"{group}-01", group) for group in ("LITHO", "ETCH", "INSPECT")
        ),
        lots=tuple(Lot(f"LOT-{i:03d}", 0, 150, list(steps)) for i in range(1, 21)),
        transport=TransportConfig(vehicle_count, travel_time=5),
    )
