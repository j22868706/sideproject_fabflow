"""HTTP checks for synchronous run creation and stored result queries."""

from dataclasses import asdict

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.models.simulation import EventResponse, MetricsResponse
from simulator.engine import SimulationEngine
from simulator.policies.critical_ratio import CriticalRatioPolicy
from simulator.policies.fifo import FIFOPolicy
from simulator.policies.spt import SPTPolicy
from simulator.scenarios.comparison import create_comparison_scenario


def request_payload(policy="FIFO"):
    scenario = asdict(create_comparison_scenario())
    scenario["transport"] = {"vehicle_count": 1, "travel_time": 3}
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
    return {"scenario": scenario, "policy": policy, "normal_wait_threshold": 15}


@pytest.mark.parametrize(
    ("name", "policy"), [("FIFO", FIFOPolicy), ("SPT", SPTPolicy), ("CR", CriticalRatioPolicy)]
)
def test_http_results_match_engine(name, policy):
    from app.models.simulation import RunCreate

    payload = request_payload(name)
    request = RunCreate.model_validate(payload)
    expected = SimulationEngine(42, policy(), normal_wait_threshold=15).run_scenario(
        request.scenario.to_domain()
    )
    with TestClient(create_app()) as client:
        response = client.post("/api/v1/runs", json=payload)
        assert response.status_code == 201
        summary = response.json()
        location = response.headers["Location"]
        assert location == f"/api/v1/runs/{summary['run_id']}"
        assert summary["status"] == "completed"
        assert summary["completed_lots"] == 12
        assert summary["policy"] == name
        assert summary["normal_wait_threshold"] == 15
        assert summary["finished_at"] == expected.finished_at
        fetched = client.get(location)
        assert fetched.status_code == 200
        assert fetched.json() == summary
        metrics = client.get(f"{location}/metrics")
        assert metrics.status_code == 200
        assert metrics.json() == MetricsResponse.model_validate(expected.kpis).model_dump(
            mode="json"
        )
        events = client.get(f"{location}/events")
        assert events.status_code == 200
        assert events.json() == [
            EventResponse.model_validate(event).model_dump(mode="json") for event in expected.events
        ]


def test_repeated_runs_have_unique_ids_and_stable_results():
    with TestClient(create_app()) as client:
        first = client.post("/api/v1/runs", json=request_payload()).json()
        second = client.post("/api/v1/runs", json=request_payload()).json()
        assert first["run_id"] != second["run_id"]
        for suffix in ("metrics", "events"):
            first_data = client.get(f"/api/v1/runs/{first['run_id']}/{suffix}").json()
            second_data = client.get(f"/api/v1/runs/{second['run_id']}/{suffix}").json()
            assert first_data == second_data


def test_application_stores_are_isolated():
    with TestClient(create_app()) as first, TestClient(create_app()) as second:
        response = first.post("/api/v1/runs", json=request_payload())
        location = response.headers["Location"]
        assert first.get(location).status_code == 200
        for suffix in ("", "/metrics", "/events"):
            assert second.get(location + suffix).status_code == 404


def test_openapi_contains_run_endpoints():
    with TestClient(create_app()) as client:
        schema = client.get("/openapi.json").json()
        assert "post" in schema["paths"]["/api/v1/runs"]
        for suffix in ("", "/metrics", "/events"):
            assert "get" in schema["paths"]["/api/v1/runs/{run_id}" + suffix]
