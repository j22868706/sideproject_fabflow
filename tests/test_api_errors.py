"""HTTP validation failures and lifecycle health checks."""

import json

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from tests.test_api_runs import request_payload


@pytest.mark.parametrize("case", ["policy", "route", "due_date", "duplicate", "nan", "infinity"])
def test_invalid_requests_return_json_without_running_engine(case, monkeypatch):
    application = create_app()

    def unexpected_create(request):
        pytest.fail("Invalid requests must not execute a simulation")

    monkeypatch.setattr(application.state.run_service, "create", unexpected_create)
    payload = request_payload()
    if case == "policy":
        payload["policy"] = "unknown"
    elif case == "route":
        payload["scenario"]["lots"][0]["route"] = ["missing"]
    elif case == "due_date":
        payload["scenario"]["lots"][0].update(arrival_time=10, due_date=1)
    elif case == "duplicate":
        payload["scenario"]["lots"].append(payload["scenario"]["lots"][0].copy())
    else:
        payload["normal_wait_threshold"] = float("nan" if case == "nan" else "inf")
    with TestClient(application) as client:
        response = client.post(
            "/api/v1/runs",
            content=json.dumps(payload),
            headers={"Content-Type": "application/json"},
        )
    assert response.status_code == 422
    issues = response.json()["detail"]
    assert issues
    assert all(set(issue) == {"loc", "msg", "type"} for issue in issues)
    assert all(issue["loc"][0] == "body" for issue in issues)


@pytest.mark.parametrize("content", ["{", "", "null"])
def test_malformed_or_missing_body(content):
    with TestClient(create_app()) as client:
        response = client.post(
            "/api/v1/runs", content=content, headers={"Content-Type": "application/json"}
        )
    assert response.status_code == 422
    assert response.json()["detail"]


@pytest.mark.parametrize("suffix", ["", "/metrics", "/events"])
def test_unknown_run(suffix):
    with TestClient(create_app()) as client:
        response = client.get("/api/v1/runs/missing" + suffix)
    assert response.status_code == 404
    assert response.json() == {"detail": "Run not found"}


def test_health_tracks_lifecycle_and_store_availability():
    application = create_app()
    assert application.state.ready is False
    with TestClient(application) as client:
        assert client.get("/health/live").json() == {"status": "alive"}
        response = client.get("/health/ready")
        assert response.status_code == 200
        assert response.json() == {"status": "ready"}
        service = application.state.run_service
        application.state.run_service = None
        assert client.get("/health/live").status_code == 200
        assert client.get("/health/ready").status_code == 503
        application.state.run_service = service
        assert client.get("/health/ready").status_code == 200
    assert application.state.ready is False


def test_not_ready_blocks_run_access():
    application = create_app()
    with TestClient(application) as client:
        application.state.ready = False
        for path in ("/health/ready", "/api/v1/runs/missing"):
            response = client.get(path)
            assert response.status_code == 503
            assert response.json() == {"detail": "Service not ready"}
        assert client.post("/api/v1/runs", json=request_payload()).status_code == 503
        assert client.get("/health/live").status_code == 200


def test_unexpected_failure_is_logged_and_returns_generic_json(monkeypatch, caplog):
    from simulator.engine import SimulationEngine

    def fail(self, scenario):
        raise RuntimeError("internal diagnostic")

    def unexpected_save(run):
        pytest.fail("Failed simulations must not save results")

    monkeypatch.setattr(SimulationEngine, "run_scenario", fail)
    application = create_app()
    monkeypatch.setattr(application.state.run_service._store, "save", unexpected_save)

    with TestClient(application, raise_server_exceptions=False) as client:
        response = client.post("/api/v1/runs", json=request_payload())
        assert response.status_code == 500
        assert response.json() == {"detail": "Internal server error"}
        assert client.get("/health/ready").status_code == 200

    assert "internal diagnostic" in caplog.text


def test_openapi_describes_error_responses_and_health():
    with TestClient(create_app()) as client:
        paths = client.get("/openapi.json").json()["paths"]
    assert "200" in paths["/health/live"]["get"]["responses"]
    assert "503" in paths["/health/ready"]["get"]["responses"]
    responses = paths["/api/v1/runs"]["post"]["responses"]
    assert responses["422"]["content"]["application/json"]["schema"]["$ref"].endswith(
        "/ValidationErrorResponse"
    )


def test_storage_failure_returns_generic_error(monkeypatch):
    from app.services.run_store import RunStoreError

    def fail_save(run):
        raise RunStoreError("internal storage diagnostic")

    application = create_app()
    monkeypatch.setattr(application.state.run_service._store, "save", fail_save)

    with TestClient(application, raise_server_exceptions=False) as client:
        response = client.post("/api/v1/runs", json=request_payload())

    assert response.status_code == 500
    assert response.json() == {"detail": "Internal server error"}
    assert "Location" not in response.headers


def test_storage_unavailable_returns_503(monkeypatch):
    from app.services.run_store import RunStoreUnavailable

    def fail_save(run):
        raise RunStoreUnavailable("private connection diagnostic")

    application = create_app()
    monkeypatch.setattr(application.state.run_service._store, "save", fail_save)

    with TestClient(application) as client:
        response = client.post("/api/v1/runs", json=request_payload())

    assert response.status_code == 503
    assert response.json() == {"detail": "Result storage is unavailable"}
    assert "Location" not in response.headers
