from simulator.entities.lot import Lot, LotPriority
from simulator.entities.process_step import ProcessStep
from simulator.entities.scenario import MachineConfig, SimulationScenario


def create_baseline_scenario(seed: int = 42) -> SimulationScenario:
    steps = (
        ProcessStep(
            step_id="STEP-LITHO",
            name="Lithography",
            processing_time=10.0,
            eligible_machine_group="LITHO",
        ),
        ProcessStep(
            step_id="STEP-ETCH",
            name="Etching",
            processing_time=8.0,
            eligible_machine_group="ETCH",
        ),
        ProcessStep(
            step_id="STEP-INSPECT",
            name="Inspection",
            processing_time=5.0,
            eligible_machine_group="INSPECT",
        ),
    )

    machines = (
        MachineConfig(machine_id="LITHO-01", group="LITHO"),
        MachineConfig(machine_id="LITHO-02", group="LITHO"),
        MachineConfig(machine_id="ETCH-01", group="ETCH"),
        MachineConfig(machine_id="INSPECT-01", group="INSPECT"),
    )

    lots = tuple(
        Lot(
            lot_id=f"LOT-{index + 1:03d}",
            arrival_time=float(index * 3),
            due_date=120.0,
            route=list(steps),
            priority=LotPriority.HOT if index == 0 else LotPriority.NORMAL,
        )
        for index in range(5)
    )

    return SimulationScenario(
        scenario_id="three-stage-baseline",
        seed=seed,
        process_steps=steps,
        machines=machines,
        lots=lots,
    )


def main() -> None:
    scenario = create_baseline_scenario()

    print(f"Scenario: {scenario.scenario_id}")
    print(f"Seed: {scenario.seed}")
    print(f"Stages: {len(scenario.process_steps)}")
    print(f"Machines: {len(scenario.machines)}")
    print(f"Lots: {len(scenario.lots)}")
    print("Route: " + " -> ".join(step.name for step in scenario.process_steps))


if __name__ == "__main__":
    main()
