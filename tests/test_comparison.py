import json
import subprocess
import sys

from app.simulation.compare import compare_policies
from simulator.scenarios.comparison import create_comparison_scenario


def test_comparison_uses_identical_failure_calendars_and_fresh_inputs():
    scenario = create_comparison_scenario()
    report = compare_policies(scenario)
    assert report == compare_policies(scenario)
    assert all(lot.completed_at is None for lot in scenario.lots)
    assert len({tuple(run["completion_order"]) for run in report["runs"]}) == 3
    horizon = min(run["kpis"]["observation_minutes"] for run in report["runs"])
    calendars = [
        [
            event
            for event in run["events"]
            if event["lot_id"] is None and event["timestamp"] < horizon
        ]
        for run in report["runs"]
    ]
    assert calendars[0]
    assert calendars[0] == calendars[1] == calendars[2]
    assert all(run["kpis"]["completed_lots"] == 12 for run in report["runs"])


def test_comparison_cli_exports_markdown_and_json(tmp_path):
    markdown = tmp_path / "report.md"
    data = tmp_path / "report.json"
    subprocess.run(
        [
            sys.executable,
            "-m",
            "app.simulation.compare",
            "--output",
            str(markdown),
            "--json",
            str(data),
        ],
        check=True,
    )
    report = json.loads(data.read_text())
    assert report["scenario"]["seed"] == 42
    assert len(report["runs"]) == 3
    assert "CriticalRatioPolicy" in markdown.read_text()
    assert "Machine metrics" in markdown.read_text()
