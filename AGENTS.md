# Repository Guidelines

## Project Structure & Module Organization

FabFlow is a Python 3.12+ discrete-event simulator for synthetic semiconductor manufacturing. The seven-day MVP is complete: multi-stage SimPy simulation, dispatching, reliability, AMHS, KPIs, a synchronous FastAPI service, a Streamlit dashboard, Docker Compose, and delivery documentation.

- `simulator/engine.py`: simulation scheduling, lifecycle transitions, and results.
- `simulator/entities/`: lot, machine, process-step, and queue models.
- `simulator/events/`: event types and immutable event records.
- `tests/`: Pytest simulator, API, and dashboard tests.
- `docs/`: domain definitions, baseline scenarios, acceptance records, runbook, and portfolio.
- `app/cli.py`: informational CLI entry point; `app/simulation/` contains executable demos.
- `app/main.py`, `app/api/`, `app/models/`, `app/services/`: API lifecycle, routes, schemas, and in-memory run results.
- `simulator/policies/`, `simulator/metrics/`: FIFO/SPT/CR with Hot/aging rules and KPI calculation.
- `app/dashboard/`: Streamlit scenario controls, API client, manufacturing KPIs, and equipment/AMHS charts.
- `deployments/k8s/`: API and dashboard Kubernetes manifests.
- `docs/k8s/`: follow-up Kubernetes learning and verification records.
- `scripts/`: container HTTP and real-browser acceptance scripts.

MVP Days 6–7 completed dashboard controls/charts, Docker Compose, browser acceptance, final verification, and handoff. See `docs/day6-dashboard.md` and `docs/day7-delivery.md`. Install `.[dashboard]` to run the dashboard. Persistent storage and monitoring remain outside the seven-day MVP. API results are process-local and lost on restart; use one worker.

The separate Kubernetes learning track has completed Days 1–7, including kind deployment, API/dashboard networking, health probes, resource settings, and troubleshooting. Day 7 records Service targetPort and dashboard API URL failures, recovery, and final UI acceptance based on user-provided outputs and confirmations; see `docs/k8s/day07-debugging.md`. Day 8 core operational acceptance is complete: namespace rebuild, old run returning 404, and successful new baseline/UI checks; see `docs/k8s/day08-rebuild.md`. Service DNS and label selector clarification was provided after the user answered the conceptual check. The original 30-day plan is `FabFlow_K8s_30天進度表.xlsx`; consult it before choosing the next lesson. Day 9 storage design and guided conceptual exercises are complete; see `docs/k8s/day09-storage-design.md`. Day 10 PostgreSQL development setup and guided verification are complete; see `docs/k8s/day10-postgres-dev.md`. Compose has a PostgreSQL 17 service and named volume, initialization SQL, and API PG environment variables with psycopg. User-provided outputs verify API-container DB connectivity and table visibility; the default application still uses memory. Day 11 completed the storage interface, MemoryRunStore delegation, PostgreSQL save, injectable create_app store, and storage-unavailable HTTP 503 handling; see `docs/k8s/day11-postgres-write.md`. User outputs verify complete JSON round-trip (12 lots, 142 events), committed results after HTTP 201, and real connection failure returning 503 through an explicitly injected temporary HTTP server. PostgresRunStore currently has save only and does not yet fully implement RunStore; get, production backend selection, restart persistence, and query failures remain for Day 12. Do not switch the default API to this partial adapter before completing queries. Copy `.env.example` to `.env` and set a local password before Compose commands; never commit real credentials. The workbook status is synchronized through Day 11 (11/30 complete); actual hours remain unrecorded. For lessons, follow the user’s preference to teach one step at a time and wait for their work before continuing; do not implement an entire lesson in advance. Recheck live cluster state before continuing; historical records do not establish current cluster health.

## Build, Test, and Development Commands

Run commands from the repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
ruff check .
ruff format --check .
pytest -v
pytest --cov=app --cov=simulator --cov-report=term-missing
```

The editable installation includes development tools. Install `.[dev,dashboard]` for dashboard development and the complete test suite; `.[browser]` adds Playwright for browser acceptance. Ruff checks lint and formatting; Pytest runs the suite and optionally reports coverage. Use `ruff format .` to apply formatting. The installed `fabflow` command prints project information; execute simulations through `app.simulation` modules, the Python API, HTTP API, or dashboard. See `docs/runbook.md` for startup and acceptance commands.

## Coding Style & Naming Conventions

Use four-space indentation, double quotes, and a 100-character line limit. Follow the Ruff configuration in `pyproject.toml`, including import sorting. Use `snake_case` for modules, functions, and variables, `PascalCase` for classes, and uppercase enum members. Add type annotations consistent with existing code and keep simulation behavior in `simulator/`.

## Testing Guidelines

Name files `tests/test_*.py` and test functions `test_*`. Add focused behavioral tests for changed simulation rules, including timestamps, queue state, capacity, and event ordering. Use fresh engines and entities for independent runs. Keep scenarios deterministic; use the engine-owned random generator when adding stochastic behavior.

Consult `docs/baseline-scenario.md` when adding acceptance tests; the existing engine fixture uses different inputs. Coverage includes branches for `app` and `simulator`; no minimum percentage is enforced. CI requires lint, formatting, and tests to pass.

## Commit & Pull Request Guidelines

Existing commits use concise prefixes such as `feat:`, `docs:`, and `chore:`. Continue this pattern with an imperative summary. Keep changes focused. PR descriptions should explain the problem, resulting behavior, and validation commands, link relevant issues when applicable, and update documentation when assumptions or supported behavior change.
