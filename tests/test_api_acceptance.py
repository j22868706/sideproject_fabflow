"""Acceptance checks using the same JSON examples as the Swagger walkthrough."""

import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import create_app

EXAMPLES = Path(__file__).resolve().parents[1] / "docs" / "examples"


@pytest.mark.parametrize(
    ("name", "finish", "cycle", "jobs"),
    [("baseline", 175, 70.5, 0), ("amhs_bottleneck", 203, 142.75, 40)],
)
def test_documented_examples_complete_full_workflow(name, finish, cycle, jobs):
    payload = json.loads((EXAMPLES / f"{name}.json").read_text())
    with TestClient(create_app()) as client:
        assert client.get("/health/ready").status_code == 200
        created = client.post("/api/v1/runs", json=payload)
        assert created.status_code == 201
        location = created.headers["Location"]
        summary = client.get(location).json()
        assert summary == created.json()
        assert summary["completed_lots"] == 20
        assert summary["finished_at"] == finish
        metrics = client.get(location + "/metrics").json()
        assert metrics["average_cycle_time"] == cycle
        assert metrics["throughput_per_hour"] == pytest.approx(20 * 60 / finish)
        assert metrics["transport_job_count"] == jobs
        events = client.get(location + "/events").json()
        assert [e["timestamp"] for e in events] == sorted(e["timestamp"] for e in events)
        completed = [e for e in events if e["event_type"] == "LOT_COMPLETED"]
        assert len(completed) == 20
        assert {e["lot_id"] for e in completed} == {
            lot["lot_id"] for lot in payload["scenario"]["lots"]
        }
        assert max(e["timestamp"] for e in completed) == finish
        for lot in payload["scenario"]["lots"]:
            steps = [
                e["step_id"]
                for e in events
                if e["lot_id"] == lot["lot_id"] and e["event_type"] == "PROCESS_COMPLETED"
            ]
            assert steps == lot["route"]


def test_concurrent_requests_keep_results_separate():
    baseline = json.loads((EXAMPLES / "baseline.json").read_text())
    transport = json.loads((EXAMPLES / "amhs_bottleneck.json").read_text())
    with TestClient(create_app()) as client:
        with ThreadPoolExecutor(max_workers=4) as pool:
            responses = list(
                pool.map(
                    lambda payload: client.post("/api/v1/runs", json=payload),
                    [baseline, transport, baseline, transport],
                )
            )
        assert all(response.status_code == 201 for response in responses)
        assert len({response.json()["run_id"] for response in responses}) == 4
        for response, cycle in zip(responses, [70.5, 142.75, 70.5, 142.75], strict=True):
            metrics = client.get(response.headers["Location"] + "/metrics").json()
            assert metrics["average_cycle_time"] == cycle


def test_invalid_request_does_not_prevent_next_valid_run():
    payload = json.loads((EXAMPLES / "baseline.json").read_text())
    with TestClient(create_app()) as client:
        assert client.post("/api/v1/runs", json=payload | {"policy": "invalid"}).status_code == 422
        assert client.post("/api/v1/runs", json=payload).status_code == 201
        assert client.get("/health/ready").status_code == 200


def test_swagger_page_points_to_openapi_contract():
    with TestClient(create_app()) as client:
        page = client.get("/docs")
        assert page.status_code == 200
        assert "/openapi.json" in page.text
        schema = client.get("/openapi.json").json()
        request_schema = schema["paths"]["/api/v1/runs"]["post"]["requestBody"]
        assert request_schema["content"]["application/json"]["schema"]["$ref"].endswith(
            "/RunCreate"
        )
