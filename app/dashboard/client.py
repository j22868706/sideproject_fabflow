"""Build preset requests and validate dashboard API addresses."""

from dataclasses import asdict

import httpx

from app.models.simulation import PolicyName, RunCreate
from simulator.scenarios.amhs import create_amhs_scenario
from simulator.scenarios.baseline import create_baseline_scenario

PRESETS = ("Three-stage baseline", "AMHS bottleneck")


def validate_api_url(api_url: str) -> None:
    url = httpx.URL(api_url)
    if url.scheme not in {"http", "https"} or not url.host or url.query or url.fragment:
        raise ValueError("Enter an HTTP or HTTPS base URL without a query or fragment.")


def build_request(preset: str, policy: PolicyName, threshold: float) -> RunCreate:
    """Reuse existing scenario factories; run simulations only through the API."""
    if preset == PRESETS[0]:
        scenario = create_baseline_scenario(number_of_lots=20)
    elif preset == PRESETS[1]:
        scenario = create_amhs_scenario()
    else:
        raise ValueError("Unknown scenario preset.")
    data = asdict(scenario)
    data["lots"] = [
        {
            "lot_id": lot.lot_id,
            "arrival_time": lot.arrival_time,
            "due_date": lot.due_date,
            "priority": lot.priority,
            "route": [step.step_id for step in lot.route],
        }
        for lot in scenario.lots
    ]
    return RunCreate.model_validate(
        {"scenario": data, "policy": policy, "normal_wait_threshold": threshold}
    )
