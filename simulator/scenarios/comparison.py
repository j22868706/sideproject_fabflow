"""Heterogeneous synthetic workload for comparing dispatching policies."""

from simulator.entities.lot import Lot, LotPriority
from simulator.entities.process_step import ProcessStep
from simulator.entities.reliability import ReliabilityConfig
from simulator.entities.scenario import MachineConfig, SimulationScenario


def create_comparison_scenario(seed: int = 42) -> SimulationScenario:
    steps = []
    lots = []
    for index in range(12):
        route = [
            ProcessStep(f"{group}-{index}", group, duration, group)
            for group, duration in zip(
                ("LITHO", "ETCH", "INSPECT"),
                ((10, 3, 7, 5)[index % 4], (4, 9, 2)[index % 3], 2),
                strict=True,
            )
        ]
        steps.extend(route)
        arrival = float(index * 2)
        lots.append(
            Lot(
                f"LOT-{index + 1:03d}",
                arrival,
                arrival + 25 + index % 3 * 10,
                route,
                priority=LotPriority.HOT if index % 4 == 3 else LotPriority.NORMAL,
            )
        )
    return SimulationScenario(
        "day3-policy-comparison",
        seed,
        tuple(steps),
        (
            MachineConfig("LITHO-01", "LITHO", reliability=ReliabilityConfig(mtbf=35, mttr=4)),
            MachineConfig("ETCH-01", "ETCH", reliability=ReliabilityConfig(mtbf=40, mttr=3)),
            MachineConfig("INSPECT-01", "INSPECT"),
        ),
        tuple(lots),
    )
