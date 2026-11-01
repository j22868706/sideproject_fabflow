"""Run inside the API container across an explicitly performed restart or DB outage."""

import argparse
import json
from dataclasses import asdict
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from uuid import uuid4

from simulator.scenarios.comparison import create_comparison_scenario

ENDPOINTS = (("summary", ""), ("metrics", "/metrics"), ("events", "/events"))


def request_json(url: str, payload: dict | None = None) -> tuple[int, dict | list, dict]:
    request = Request(
        url,
        data=json.dumps(payload).encode() if payload is not None else None,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urlopen(request, timeout=30) as response:
            headers = {key.lower(): value for key, value in response.headers.items()}
            return response.status, json.load(response), headers
    except HTTPError as exc:
        with exc:
            headers = {key.lower(): value for key, value in exc.headers.items()}
            return exc.code, json.load(exc), headers


def prepare(base: str, path: Path) -> None:
    if path.exists():
        raise FileExistsError(f"Snapshot already exists; use a new --snapshot path: {path}")
    scenario = asdict(create_comparison_scenario())
    scenario["lots"] = [
        {
            "lot_id": lot["lot_id"],
            "arrival_time": lot["arrival_time"],
            "due_date": lot["due_date"],
            "priority": lot["priority"],
            "route": [step["step_id"] for step in lot["route"]],
        }
        for lot in scenario["lots"]
    ]
    status, summary, headers = request_json(
        base, {"scenario": scenario, "policy": "FIFO", "normal_wait_threshold": 15}
    )
    assert status == 201, f"Expected 201, got {status}: {summary}"
    assert isinstance(summary, dict)
    run_id = summary["run_id"]
    assert headers.get("location") == f"/api/v1/runs/{run_id}"
    snapshot = {"run_id": run_id}
    for key, suffix in ENDPOINTS:
        status, body, _ = request_json(f"{base}/{run_id}{suffix}")
        assert status == 200, f"Expected 200 for {key}, got {status}"
        snapshot[key] = body
    assert snapshot["summary"] == summary
    assert summary["completed_lots"] == 12
    assert len(snapshot["events"]) == 142
    with path.open("x", encoding="utf-8") as output:
        json.dump(snapshot, output, ensure_ascii=False)
    print(f"run_id: {run_id}")
    print(f"snapshot: {path}")
    print("PASS: HTTP 201 + Location; complete pre-restart snapshot saved")


def verify(base: str, snapshot: dict) -> None:
    run_id = snapshot["run_id"]
    for key, suffix in ENDPOINTS:
        status, body, _ = request_json(f"{base}/{run_id}{suffix}")
        assert status == 200, f"Expected 200 for {key}, got {status}"
        assert body == snapshot[key], f"Saved result changed: {key}"
        print(f"PASS: {key} matches pre-restart snapshot")
    unknown_id = str(uuid4())
    for key, suffix in ENDPOINTS:
        status, body, _ = request_json(f"{base}/{unknown_id}{suffix}")
        assert status == 404, f"Expected 404 for unknown {key}, got {status}"
        assert body == {"detail": "Run not found"}
        print(f"PASS: unknown ID returns HTTP 404 for {key}")
    print(f"run_id: {run_id}")


def unavailable(base: str, snapshot: dict) -> None:
    for run_id in (snapshot["run_id"], str(uuid4())):
        for key, suffix in ENDPOINTS:
            status, body, _ = request_json(f"{base}/{run_id}{suffix}")
            assert status == 503, f"Expected 503 for {key}, got {status}"
            assert body == {"detail": "Result storage is unavailable"}
            print(f"PASS: storage outage returns HTTP 503 for {key}; ID={run_id}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("prepare", "verify", "unavailable"))
    parser.add_argument("--api-url", default="http://127.0.0.1:8000")
    parser.add_argument("--snapshot", type=Path, default=Path("/tmp/fabflow-day12-check.json"))
    args = parser.parse_args()
    base = args.api_url.rstrip("/") + "/api/v1/runs"
    if args.action == "prepare":
        prepare(base, args.snapshot)
    else:
        snapshot = json.loads(args.snapshot.read_text(encoding="utf-8"))
        if args.action == "verify":
            verify(base, snapshot)
        else:
            unavailable(base, snapshot)


if __name__ == "__main__":
    main()
