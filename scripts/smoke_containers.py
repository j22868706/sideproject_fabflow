"""Run inside the dashboard container to verify the Compose stack over HTTP."""

import json
import os
from urllib.request import Request, urlopen

from app.dashboard.client import PRESETS, build_request


def request_json(url: str, payload: dict | None = None) -> tuple[int, dict | list]:
    request = Request(
        url,
        data=json.dumps(payload).encode() if payload is not None else None,
        headers={"Content-Type": "application/json"},
    )
    with urlopen(request, timeout=60) as response:
        return response.status, json.load(response)


def main() -> None:
    api_url = os.environ.get("FABFLOW_API_URL", "http://api:8000").rstrip("/")
    assert request_json(f"{api_url}/health/ready") == (200, {"status": "ready"})
    with urlopen("http://127.0.0.1:8501/_stcore/health", timeout=10) as response:
        assert response.status == 200
        assert response.read().strip() == b"ok"
    with urlopen("http://127.0.0.1:8501", timeout=10) as response:
        assert response.status == 200
        assert b"streamlit" in response.read().lower()

    for preset, finish, cycle, jobs in (
        (PRESETS[0], 175, 70.5, 0),
        (PRESETS[1], 203, 142.75, 40),
    ):
        status, summary = request_json(
            f"{api_url}/api/v1/runs", build_request(preset, "FIFO", 60).model_dump(mode="json")
        )
        assert status == 201
        assert summary["completed_lots"] == 20
        assert summary["finished_at"] == finish
        run_url = f"{api_url}/api/v1/runs/{summary['run_id']}"
        assert request_json(run_url) == (200, summary)
        status, metrics = request_json(f"{run_url}/metrics")
        assert status == 200
        assert metrics["average_cycle_time"] == cycle
        assert metrics["transport_job_count"] == jobs
        status, events = request_json(f"{run_url}/events")
        assert status == 200
        assert sum(event["event_type"] == "LOT_COMPLETED" for event in events) == 20
        print(f"PASS: {preset}; finish={finish}, cycle={cycle}, transport_jobs={jobs}")
    print(
        "PASS: dashboard health/HTML, API readiness, and both create/query/metrics/events workflows"
    )


if __name__ == "__main__":
    main()
