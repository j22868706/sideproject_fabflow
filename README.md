# FabFlow

FabFlow is a reproducible discrete-event simulation platform for studying
wafer-lot dispatching policies and Automated Material Handling System (AMHS)
constraints in a simplified semiconductor manufacturing environment.

The project is designed as an intelligent-manufacturing engineering portfolio
project. It emphasizes deterministic simulation, measurable scheduling
trade-offs, automated testing, API design, visualization, and container deployment.

## Project Status

Day 1 project setup and Day 2 three-stage simulation are implemented and locally
validated. Day 3 dispatching policies, equipment reliability, and KPI comparison
are next.

The current implementation provides a deterministic, multi-stage,
multi-machine simulation engine built with SimPy. It includes validated domain
entities, FIFO resource queueing, structured lifecycle events, fixed-seed
execution, and automated tests.

### Implemented

- `Lot`, `ProcessStep`, `Machine`, and `Queue` domain entities
- `SimulationScenario` and `MachineConfig` for validated experiment inputs
- `SimulationResult` and immutable `SimulationEvent` records
- Three-stage execution: Lithography → Etching → Inspection
- A five-lot scenario preview and a 20-lot executable demo
- Average cycle time and throughput calculated from simulation results
- Normal and hot lot priority classifications
- Lot and machine lifecycle status tracking
- Machine-group FIFO queues and per-machine capacity enforcement with SimPy
- Lot arrival, queueing, processing, and completion events
- Structured in-memory event logging with process-step and machine identifiers
- Fixed-seed simulation execution
- Deterministic baseline tests
- Pytest unit tests
- Ruff linting and formatting

### Planned

- FIFO, Shortest Processing Time, and Critical Ratio policy abstractions
- Machine failure and repair behavior
- Remaining KPI calculations and policy comparison reports
- Simplified AMHS transportation
- FastAPI service
- Streamlit policy comparison dashboard
- Docker Compose deployment for the API and dashboard

## Problem Statement

Semiconductor manufacturing requires production lots to move through multiple
process stages while competing for limited machines and transportation
resources. Dispatching decisions affect cycle time, work in process (WIP),
throughput, equipment utilization, queue waiting time, and on-time delivery.

FabFlow provides a controlled simulation environment for studying these
trade-offs under repeatable experimental conditions. The same scenario and
random seed can be reused across dispatching policies so that results can be
compared fairly.

## Goals

- Build a reproducible discrete-event simulation of lot production and transport.
- Compare dispatching policies using identical scenarios and random seeds.
- Quantify cycle time, throughput, WIP, utilization, and on-time delivery.
- Expose experiment creation and results through a FastAPI service.
- Visualize results and scheduling trade-offs in Streamlit.
- Run the API and dashboard with Docker Compose.

## Planned MVP

- Three process stages: Lithography, Etching, and Inspection
- One to two machines per stage
- Normal lots and high-priority hot lots
- Processing, queueing, transport, machine failure, and repair events
- FIFO, Shortest Processing Time, and Critical Ratio dispatching policies
- Fixed random seeds for reproducible experiments
- FastAPI endpoints to create runs with scenario inputs and query results, events, and metrics
- A Streamlit dashboard comparing FIFO, Shortest Processing Time, and Critical Ratio
- Docker Compose services for the API and Streamlit dashboard

## Current Simulation Flow

```mermaid
flowchart LR
    A[Lot arrives] --> Q[Lot enters queue]
    Q --> W[Lot requests machine]
    W --> P[Processing starts]
    P --> C[Processing completes]
    C --> N{More route steps?}
    N -->|Yes| Q
    N -->|No| D[Lot completes]
```

Each station has a shared FIFO queue. The engine assigns waiting lots to
available capacity slots on eligible machines and uses SimPy resources to
enforce each machine's capacity. Equal-time requests follow deterministic
SimPy/input order. A lot completes only after every route step finishes.
Explicit dispatching policy classes are planned for Day 3.

## Target Architecture

```mermaid
flowchart TD
    U[Streamlit Dashboard] --> API[FastAPI]
    API --> S[SimPy Engine]
    S --> R[In-memory Results and Events]
    API --> R
```

This diagram represents the target MVP architecture. The API will execute
simulations synchronously and retain results in memory. API endpoints, the
dashboard, and Docker Compose deployment remain planned.

## Current Repository Structure

```text
fabflow/
├── app/
│   ├── cli.py
│   └── simulation/
│       └── demo.py
├── simulator/
│   ├── engine.py
│   ├── entities/
│   │   ├── lot.py
│   │   ├── machine.py
│   │   ├── process_step.py
│   │   ├── queue.py
│   │   └── scenario.py
│   ├── events/
│   │   └── event.py
│   └── scenarios/
│       └── baseline.py
├── tests/
├── docs/
│   ├── baseline-scenario.md
│   ├── day2-walkthrough.md
│   └── domain-model.md
├── pyproject.toml
└── README.md
```

## Target Repository Structure

```text
fabflow/
├── app/
│   ├── api/              # HTTP endpoints and request validation
│   ├── core/             # Configuration and shared infrastructure
│   ├── models/           # API request and response models
│   └── services/         # Application use cases
├── simulator/
│   ├── entities/         # Simulation domain entities
│   ├── events/           # Event definitions and event log
│   ├── scenarios/        # Reproducible scenario factories
│   ├── policies/         # Dispatching policies
│   └── metrics/          # KPI calculations
├── dashboard/            # Experiment and comparison interface
├── Dockerfile            # API container
├── docker-compose.yml    # API and dashboard services
├── experiments/          # Controlled experiment definitions
├── tests/                # Unit and integration tests
├── docs/                 # Architecture and domain documentation
├── pyproject.toml
└── README.md
```

## Local Development

### Requirements

- Python 3.12 (the development and CI baseline)
- Git

### Setup

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

### Verify the Project

Run all automated checks before committing changes:

```bash
ruff format --check .
ruff check .
pytest -v
```

To apply Ruff formatting automatically:

```bash
ruff format .
```

### Create the Three-Stage Scenario

After installation, run from the repository root:

```bash
python -m simulator.scenarios.baseline
```

Expected output:

```text
Scenario: three-stage-baseline
Seed: 42
Stages: 3
Machines: 4
Lots: 5
Route: Lithography -> Etching -> Inspection
```

`SimulationScenario` groups the seed, process steps, machine configurations,
and lots. The example contains two Lithography machines, one Etching machine,
and one Inspection machine, with four Normal lots and one Hot lot. All times
are synthetic and expressed in minutes.

This command creates and describes the scenario. `SimulationEngine.run_scenario()`
executes every route step and copies input lots to keep scenario inputs unchanged.
Use a fresh engine with the scenario seed for each execution.

### Run the Three-Stage Demo

The installed `fabflow` command prints project information. Run the Day 2
simulation demo with:

```bash
python -m app.simulation.demo
```

```text
Completed lots: 20
Average cycle time: 70.5 minutes
Throughput: 6.86 lots/hour
```

These values are calculated from the 20-lot scenario. Throughput uses the
observation window from time zero to the last completion (175 minutes).
Normal and Hot lots currently share FIFO ordering; priority dispatching is
Day 3 work. Processing times are fixed, with no transport delays or failures.
See [Day 2 walkthrough](docs/day2-walkthrough.md) for implementation details.

### Run a Scenario in Python

```python
from simulator.engine import SimulationEngine
from simulator.scenarios.baseline import create_baseline_scenario

scenario = create_baseline_scenario(seed=42, number_of_lots=20)
result = SimulationEngine(seed=scenario.seed).run_scenario(scenario)

print(result.average_cycle_time)
print(result.throughput_per_hour)
print(result.events[0])
```

Each engine runs once. `run_scenario()` copies the scenario's lots, allowing
repeat runs with fresh engines without changing the input scenario.

### Day 2 Validation

Local validation on Python 3.12.14 passes 25 tests, Ruff lint, and Ruff formatting.
The tests cover route order, arrival and completion timestamps, eligible-machine
selection, capacity enforcement, overlapping machine activity, final empty
queues, FIFO ties, and repeatable results without input mutation.

The five-lot scenario has hand-checked completion times of 23, 31, 39, 47, and
55 minutes, with an average cycle time of 33 minutes. The original single-machine
baseline remains covered for compatibility. These are local results; remote CI
status must be checked separately.

## Determinism and Reproducibility

Each simulation engine is initialized with a fixed random seed. The current
baseline contains no stochastic behavior, so its reproducibility comes from
fixed inputs and deterministic SimPy event ordering. Later increments will use
the engine-owned random generator for processing-time variation, machine
failures, and repairs.

Fair policy comparisons will use the same:

- Random seed
- Lot arrival sequence
- Processing-time samples
- Failure and repair samples
- Simulation horizon
- Machine and AMHS configuration

## Core Metrics

The completed MVP will report:

- Average and P95 cycle time
- Throughput
- Work in process
- Queue depth and waiting time
- Machine utilization
- On-time delivery rate
- Transport time and delivery-time accuracy

Average cycle time and throughput are available on `SimulationResult`. The
remaining manufacturing KPI calculations are planned for Day 3; transport
metrics follow with the AMHS model in Day 4.

## Documentation

- [Day 2 walkthrough](docs/day2-walkthrough.md)
- [Domain Model](docs/domain-model.md)
- [Hand-Calculated Baseline Scenario](docs/baseline-scenario.md)

## Assumptions and Limitations

FabFlow does **not** use TSMC data or data from any real semiconductor
fabrication facility. All routes, processing times, machine configurations,
failures, transportation times, and events are simplified models based on
public manufacturing concepts or synthetic data.

The MVP does not attempt to reproduce the complete behavior of a real fab. It
excludes hundreds of detailed process steps, complete re-entrant routing,
complex recipe qualification, and real facility path optimization.

## Connection to Intelligent Manufacturing

FabFlow demonstrates how discrete-event simulation, scheduling, visualization,
API design, and container deployment can be combined to evaluate
manufacturing decisions.

The project also explores conceptual similarities between manufacturing
dispatching and computing-resource scheduling, including queues, priorities,
capacity constraints, fairness, and reservations. These are design analogies;
Kubernetes and Apache YuniKorn are not presented as semiconductor AMHS
dispatching systems.

## Roadmap

1. **Implemented:** project foundation, domain models, and three-stage scenario creation
2. **Implemented:** deterministic three-stage simulation engine
3. FIFO, SPT, Critical Ratio, equipment reliability, and KPI comparison
4. Simplified AMHS transportation
5. FastAPI service with synchronous simulation execution
6. Streamlit dashboard, Docker Compose, and end-to-end demo
7. Tests, documentation, and portfolio packaging

## Future Work

The following are outside the seven-day MVP:

- PostgreSQL persistence and database migrations
- Background workers and job queues such as Celery or RQ, with Redis
- Prometheus and Grafana monitoring
- Kubernetes and Kind deployment
- Stocker capacity constraints
- Advanced scheduling and large-scale performance testing

## License

This project is intended for educational and portfolio purposes.
