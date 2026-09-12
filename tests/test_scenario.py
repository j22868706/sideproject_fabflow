from dataclasses import replace

import pytest

from simulator.entities.lot import LotPriority
from simulator.scenarios.baseline import create_baseline_scenario


def test_baseline_contains_three_stages_machines_and_lots() -> None:
    scenario = create_baseline_scenario()

    assert [step.name for step in scenario.process_steps] == [
        "Lithography",
        "Etching",
        "Inspection",
    ]
    assert len(scenario.machines) == 4
    assert len(scenario.lots) == 5

    for step in scenario.process_steps:
        matching_machines = [
            machine for machine in scenario.machines if machine.group == step.eligible_machine_group
        ]
        assert 1 <= len(matching_machines) <= 2

    assert all(lot.route == list(scenario.process_steps) for lot in scenario.lots)
    assert {lot.priority for lot in scenario.lots} == {
        LotPriority.NORMAL,
        LotPriority.HOT,
    }


def test_baseline_is_repeatable_with_fresh_lots() -> None:
    first = create_baseline_scenario(seed=42)
    second = create_baseline_scenario(seed=42)

    assert first == second
    assert first.lots[0] is not second.lots[0]
    assert first.lots[0].route is not second.lots[0].route


def test_scenario_rejects_duplicate_lot_ids() -> None:
    scenario = create_baseline_scenario()
    duplicate = replace(scenario.lots[1], lot_id=scenario.lots[0].lot_id)

    with pytest.raises(ValueError, match="lot_id must be unique"):
        replace(scenario, lots=(scenario.lots[0], duplicate))


def test_scenario_rejects_missing_machine_group() -> None:
    scenario = create_baseline_scenario()
    machines = tuple(machine for machine in scenario.machines if machine.group != "ETCH")

    with pytest.raises(ValueError, match="no machine available"):
        replace(scenario, machines=machines)


def test_scenario_rejects_empty_route() -> None:
    scenario = create_baseline_scenario()
    lot = replace(scenario.lots[0], route=[])

    with pytest.raises(ValueError, match="must have a route"):
        replace(scenario, lots=(lot,))


def test_scenario_rejects_undefined_route_step() -> None:
    scenario = create_baseline_scenario()
    undefined_step = replace(
        scenario.process_steps[0],
        step_id="UNKNOWN",
    )
    lot = replace(scenario.lots[0], route=[undefined_step])

    with pytest.raises(ValueError, match="undefined process step"):
        replace(scenario, lots=(lot,))
