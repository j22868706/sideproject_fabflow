"""Synchronous simulations and process-local result storage."""

from uuid import uuid4

from app.models.simulation import EventResponse, MetricsResponse, RunCreate, RunResponse
from app.services.run_store import RunStore, StoredRun
from simulator.engine import SimulationEngine
from simulator.policies.critical_ratio import CriticalRatioPolicy
from simulator.policies.fifo import FIFOPolicy
from simulator.policies.spt import SPTPolicy


class RunService:
    """Execute simulations and delegate completed result storage."""

    def __init__(self, store: RunStore) -> None:
        self._store = store

    def create(self, request: RunCreate) -> StoredRun:
        """Run a fresh engine synchronously and store fully converted responses."""
        policies = {"FIFO": FIFOPolicy, "SPT": SPTPolicy, "CR": CriticalRatioPolicy}
        scenario = request.scenario.to_domain()
        result = SimulationEngine(
            seed=scenario.seed,
            policy=policies[request.policy](),
            normal_wait_threshold=request.normal_wait_threshold,
        ).run_scenario(scenario)
        summary = RunResponse(
            run_id=str(uuid4()),
            scenario_id=scenario.scenario_id,
            seed=scenario.seed,
            policy=request.policy,
            normal_wait_threshold=request.normal_wait_threshold,
            finished_at=result.finished_at,
            completed_lots=len(result.completed_lots),
        )
        stored = StoredRun(
            summary,
            MetricsResponse.model_validate(result.kpis),
            tuple(EventResponse.model_validate(event) for event in result.events),
        )
        # Publish only complete results; simulations do not hold the store lock.
        self._store.save(stored)
        return stored

    def get(self, run_id: str) -> StoredRun | None:
        """Look up a completed run using the configured store."""
        return self._store.get(run_id)
