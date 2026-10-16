"""API contracts for synchronous simulation runs; all durations are minutes."""

from typing import Annotated, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from simulator.entities.lot import Lot, LotPriority
from simulator.entities.process_step import ProcessStep
from simulator.entities.reliability import ReliabilityConfig
from simulator.entities.scenario import MachineConfig, SimulationScenario
from simulator.entities.transport import TransportConfig
from simulator.events.event import EventType

Identifier = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
PositiveTime = Annotated[float, Field(gt=0, allow_inf_nan=False)]
NonNegativeTime = Annotated[float, Field(ge=0, allow_inf_nan=False)]
PositiveCount = Annotated[int, Field(gt=0, strict=True)]
PolicyName = Literal["FIFO", "SPT", "CR"]


class APIModel(BaseModel):
    """Reject extra fields and non-finite numbers; allow domain-object responses."""

    model_config = ConfigDict(extra="forbid", from_attributes=True, allow_inf_nan=False)


class ProcessStepCreate(APIModel):
    step_id: Identifier
    name: Identifier
    processing_time: PositiveTime
    eligible_machine_group: Identifier


class ReliabilityCreate(APIModel):
    mtbf: PositiveTime | None = None
    mttr: PositiveTime | None = None
    outages: list[tuple[NonNegativeTime, PositiveTime]] = Field(default_factory=list)

    def to_domain(self) -> ReliabilityConfig:
        return ReliabilityConfig(self.mtbf, self.mttr, tuple(self.outages))

    @model_validator(mode="after")
    def validate_reliability(self) -> Self:
        self.to_domain()
        return self


class MachineCreate(APIModel):
    machine_id: Identifier
    group: Identifier
    capacity: PositiveCount = 1
    reliability: ReliabilityCreate | None = None


class LotCreate(APIModel):
    lot_id: Identifier
    arrival_time: NonNegativeTime
    due_date: NonNegativeTime
    route: list[Identifier] = Field(min_length=1, description="Ordered process step IDs")
    priority: LotPriority = LotPriority.NORMAL

    @model_validator(mode="after")
    def validate_due_date(self) -> Self:
        if self.due_date < self.arrival_time:
            raise ValueError("due_date must not be earlier than arrival_time")
        return self


class TransportCreate(APIModel):
    vehicle_count: PositiveCount = 1
    travel_time: NonNegativeTime = 5.0


class ScenarioCreate(APIModel):
    """Explicit manufacturing inputs with ordered process-step IDs in lot routes."""

    scenario_id: Identifier
    seed: Annotated[int, Field(strict=True)] = 42
    process_steps: list[ProcessStepCreate] = Field(min_length=1)
    machines: list[MachineCreate] = Field(min_length=1)
    lots: list[LotCreate] = Field(min_length=1)
    transport: TransportCreate | None = None

    def to_domain(self) -> SimulationScenario:
        """Build fresh domain objects, resolving route references to defined steps."""
        steps = tuple(ProcessStep(**step.model_dump()) for step in self.process_steps)
        by_id = {step.step_id: step for step in steps}
        for lot in self.lots:
            for step_id in lot.route:
                if step_id not in by_id:
                    raise ValueError(f"lot {lot.lot_id} references undefined step {step_id}")
        return SimulationScenario(
            scenario_id=self.scenario_id,
            seed=self.seed,
            process_steps=steps,
            machines=tuple(
                MachineConfig(
                    machine.machine_id,
                    machine.group,
                    machine.capacity,
                    machine.reliability.to_domain() if machine.reliability else None,
                )
                for machine in self.machines
            ),
            lots=tuple(
                Lot(
                    lot.lot_id,
                    lot.arrival_time,
                    lot.due_date,
                    [by_id[step_id] for step_id in lot.route],
                    lot.priority,
                )
                for lot in self.lots
            ),
            transport=TransportConfig(**self.transport.model_dump()) if self.transport else None,
        )

    @model_validator(mode="after")
    def validate_scenario(self) -> Self:
        self.to_domain()
        return self


class RunCreate(APIModel):
    """Select the base dispatch policy and per-station Normal lot aging threshold."""

    scenario: ScenarioCreate
    policy: PolicyName = "FIFO"
    normal_wait_threshold: PositiveTime = 60.0


class RunResponse(APIModel):
    """Summary returned after the synchronous simulation completes."""

    run_id: Identifier
    scenario_id: Identifier
    seed: int
    policy: PolicyName
    normal_wait_threshold: PositiveTime
    status: Literal["completed"] = "completed"
    finished_at: NonNegativeTime
    completed_lots: Annotated[int, Field(ge=0)]


class MachineMetricsResponse(APIModel):
    machine_id: str
    utilization: float
    availability: float
    downtime: float


class MetricsResponse(APIModel):
    """Engine KPIs over time zero through the final lot completion."""

    completed_lots: int
    observation_minutes: float
    average_cycle_time: float
    p95_cycle_time: float
    throughput_per_hour: float
    average_wip: float
    average_waiting_time: float
    average_queue_depth: float
    max_queue_depth: int
    on_time_delivery_rate: float
    average_tardiness: float
    machines: list[MachineMetricsResponse]
    average_transport_time: float
    average_transport_waiting_time: float
    vehicle_utilization: float
    transport_job_count: int


class EventResponse(APIModel):
    """Manufacturing, reliability, or transport event with applicable entity IDs."""

    timestamp: float
    event_type: EventType
    lot_id: str | None
    machine_id: str | None = None
    queue_depth: int | None = None
    step_id: str | None = None
    transport_job_id: str | None = None
    origin: str | None = None
    destination: str | None = None
