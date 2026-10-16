"""Validate the API boundary against real engine inputs and outputs."""

import json
from dataclasses import asdict

import pytest
from pydantic import ValidationError

from app.models.simulation import EventResponse, MetricsResponse, RunCreate, RunResponse
from simulator.engine import SimulationEngine


@pytest.fixture
def payload():
    return {
        "scenario": {
            "scenario_id": "api-example",
            "seed": 42,
            "process_steps": [
                {
                    "step_id": "etch",
                    "name": "Etching",
                    "processing_time": 2,
                    "eligible_machine_group": "ETCH",
                }
            ],
            "machines": [{"machine_id": "M1", "group": "ETCH"}],
            "lots": [{"lot_id": "L1", "arrival_time": 0, "due_date": 20, "route": ["etch"]}],
        }
    }


def test_request_round_trip_and_fresh_domain_inputs(payload):
    request = RunCreate.model_validate_json(json.dumps(payload))
    assert request.policy == "FIFO"
    assert request.normal_wait_threshold == 60
    first = request.scenario.to_domain()
    second = request.scenario.to_domain()
    assert first == second
    assert first.lots[0] is not second.lots[0]
    result = SimulationEngine(seed=first.seed).run_scenario(first)
    assert result.finished_at == 2
    assert second.lots[0].completed_at is None
    assert RunCreate.model_validate_json(request.model_dump_json()) == request


@pytest.mark.parametrize(
    ("target", "field", "value"),
    [
        ("run", "policy", "unknown"),
        ("run", "normal_wait_threshold", 0),
        ("run", "normal_wait_threshold", float("inf")),
        ("run", "unexpected", 1),
        ("scenario", "scenario_id", "  "),
        ("scenario", "seed", True),
        ("scenario", "lots", []),
        ("lot", "route", ["missing"]),
        ("lot", "route", []),
        ("lot", "arrival_time", -1),
        ("lot", "due_date", float("nan")),
        ("lot", "priority", "urgent"),
        ("machine", "capacity", True),
        ("machine", "capacity", 1.5),
        ("machine", "capacity", 0),
        ("machine", "group", "missing"),
        ("step", "processing_time", 0),
        ("step", "processing_time", float("inf")),
        ("scenario", "transport", {"vehicle_count": 0}),
        ("scenario", "transport", {"travel_time": -1}),
        ("machine", "reliability", {"mtbf": 10}),
        ("machine", "reliability", {"outages": [[2, 4], [3, 1]]}),
        ("machine", "reliability", {"mtbf": 10, "mttr": 1, "outages": [[2, 1]]}),
    ],
)
def test_invalid_requests_rejected(payload, target, field, value):
    scenario = payload["scenario"]
    targets = {
        "run": payload,
        "scenario": scenario,
        "lot": scenario["lots"][0],
        "machine": scenario["machines"][0],
        "step": scenario["process_steps"][0],
    }
    targets[target][field] = value
    with pytest.raises(ValidationError):
        RunCreate.model_validate(payload)


@pytest.mark.parametrize("collection", ["lots", "machines", "process_steps"])
def test_duplicate_ids_rejected(payload, collection):
    items = payload["scenario"][collection]
    items.append(items[0].copy())
    with pytest.raises(ValidationError, match="unique"):
        RunCreate.model_validate(payload)


def test_due_date_before_arrival_rejected(payload):
    payload["scenario"]["lots"][0].update(arrival_time=10, due_date=9)
    with pytest.raises(ValidationError, match="due_date"):
        RunCreate.model_validate(payload)


@pytest.mark.parametrize("policy", ["FIFO", "SPT", "CR"])
def test_policy_names_accepted(payload, policy):
    payload["policy"] = policy
    assert RunCreate.model_validate(payload).policy == policy


def test_responses_preserve_engine_kpis_and_failure_transport_events(payload):
    scenario = payload["scenario"]
    scenario["lots"][0]["route"] = ["etch", "etch"]
    scenario["machines"][0]["reliability"] = {"outages": [[1, 2]]}
    scenario["transport"] = {"vehicle_count": 1, "travel_time": 3}
    request = RunCreate.model_validate(payload)
    result = SimulationEngine(seed=42).run_scenario(request.scenario.to_domain())
    metrics = MetricsResponse.model_validate(result.kpis)
    assert json.loads(metrics.model_dump_json()) == json.loads(json.dumps(asdict(result.kpis)))
    events = [EventResponse.model_validate(event) for event in result.events]
    for event, original in zip(events, result.events, strict=True):
        assert json.loads(event.model_dump_json()) == asdict(original)
    failure = next(event for event in events if event.event_type == "MACHINE_FAILED")
    assert failure.lot_id is None
    delivery = next(event for event in events if event.event_type == "TRANSPORT_COMPLETED")
    assert delivery.transport_job_id is not None
    assert delivery.origin == delivery.destination == "ETCH"
    response = RunResponse(
        run_id="run-1",
        scenario_id=scenario["scenario_id"],
        seed=42,
        policy=request.policy,
        normal_wait_threshold=request.normal_wait_threshold,
        finished_at=result.finished_at,
        completed_lots=len(result.completed_lots),
    )
    assert response.finished_at == 9
    assert RunResponse.model_validate_json(response.model_dump_json()) == response


def test_contracts_generate_json_schema():
    for model in (RunCreate, RunResponse, MetricsResponse, EventResponse):
        assert model.model_json_schema()["type"] == "object"
