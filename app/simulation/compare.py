"""Run FIFO/SPT/CR with identical inputs and export Markdown and JSON."""

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from simulator.engine import SimulationEngine
from simulator.entities.scenario import SimulationScenario
from simulator.policies.critical_ratio import CriticalRatioPolicy
from simulator.policies.fifo import FIFOPolicy
from simulator.policies.spt import SPTPolicy
from simulator.scenarios.comparison import create_comparison_scenario


def compare_policies(scenario: SimulationScenario, normal_wait_threshold: float = 60.0) -> dict:
    runs = []
    for policy in (FIFOPolicy(), SPTPolicy(), CriticalRatioPolicy()):
        result = SimulationEngine(
            scenario.seed, policy, normal_wait_threshold=normal_wait_threshold
        ).run_scenario(scenario)
        runs.append(
            {
                "policy": type(policy).__name__,
                "kpis": asdict(result.kpis),
                "completion_order": [lot.lot_id for lot in result.completed_lots],
                "events": [asdict(event) for event in result.events],
            }
        )
    return {
        "scenario": asdict(scenario),
        "time_unit": "minutes",
        "normal_wait_threshold": normal_wait_threshold,
        "runs": runs,
    }


def render_markdown(report: dict) -> str:
    scenario = report["scenario"]
    lines = [
        "# Day 3 policy comparison",
        "",
        f"Scenario: `{scenario['scenario_id']}` · Seed: {scenario['seed']} · "
        f"Lots: {len(scenario['lots'])}",
        "",
        "Synthetic inputs; each policy uses fresh lots and the same machine failure streams.",
        "Observation window: time 0 through each policy's last completion. Times are minutes.",
        f"Hot lots take priority; Normal lots waiting at least "
        f"{report['normal_wait_threshold']:g} minutes take precedence in station FIFO order.",
        "",
        "| Policy | Finish | Avg cycle | P95 cycle | Lots/hour | Avg WIP | "
        "Avg wait/lot | Avg queue | Peak queue | On time | Avg tardiness |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for run in report["runs"]:
        k = run["kpis"]
        lines.append(
            f"| {run['policy']} | {k['observation_minutes']:.2f} | "
            f"{k['average_cycle_time']:.2f} | {k['p95_cycle_time']:.2f} | "
            f"{k['throughput_per_hour']:.2f} | {k['average_wip']:.2f} | "
            f"{k['average_waiting_time']:.2f} | {k['average_queue_depth']:.2f} | "
            f"{k['max_queue_depth']} | {k['on_time_delivery_rate']:.1%} | "
            f"{k['average_tardiness']:.2f} |"
        )
    lines.extend(
        [
            "",
            "## Machine metrics",
            "",
            "| Policy | Machine | Utilization | Availability | Downtime |",
            "| --- | --- | ---: | ---: | ---: |",
        ]
    )
    for run in report["runs"]:
        for machine in run["kpis"]["machines"]:
            lines.append(
                f"| {run['policy']} | {machine['machine_id']} | "
                f"{machine['utilization']:.1%} | {machine['availability']:.1%} | "
                f"{machine['downtime']:.2f} |"
            )
    cycle = min(report["runs"], key=lambda run: run["kpis"]["average_cycle_time"])
    otd = max(report["runs"], key=lambda run: run["kpis"]["on_time_delivery_rate"])
    lines.extend(
        [
            "",
            "## Observations",
            "",
            f"Lowest average cycle time: {cycle['policy']}. "
            f"Highest on-time delivery rate: {otd['policy']} (first policy shown if tied).",
            "These are results for one synthetic workload and seed, not a general ranking.",
            "Different finish times expose policies to different lengths of the same "
            "failure calendars.",
            "",
            "P95 uses the nearest-rank method. WIP and total queue depth are time averages.",
            "Waiting excludes time paused on a failed machine. "
            "Utilization is productive slot-minutes",
            "divided by capacity × observation time; availability excludes machine downtime.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--normal-wait-threshold", type=float, default=60.0)
    parser.add_argument("--output", type=Path, help="Write the Markdown report to this path")
    parser.add_argument("--json", type=Path, help="Write inputs, KPIs and events as JSON")
    args = parser.parse_args()
    report = compare_policies(create_comparison_scenario(args.seed), args.normal_wait_threshold)
    markdown = render_markdown(report)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(markdown)
    else:
        print(markdown, end="")
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()
