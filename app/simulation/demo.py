"""Run the deterministic Day 2 demo; all times are minutes."""

from simulator.engine import SimulationEngine
from simulator.scenarios.baseline import create_baseline_scenario


def main() -> None:
    scenario = create_baseline_scenario(number_of_lots=20)
    result = SimulationEngine(seed=scenario.seed).run_scenario(scenario)
    print(f"Completed lots: {len(result.completed_lots)}")
    print(f"Average cycle time: {result.average_cycle_time:.1f} minutes")
    print(f"Throughput: {result.throughput_per_hour:.2f} lots/hour")


if __name__ == "__main__":
    main()
