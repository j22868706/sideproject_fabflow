# FabFlow operation and handoff

FabFlow runs a synthetic, finite semiconductor workload through Lithography,
Etching, and Inspection. The dashboard calls the synchronous FastAPI service;
the API owns simulation execution. Compose stores completed results in PostgreSQL;
local Python defaults to process-local memory. Keep one API worker for this setup.
The [demo walkthrough](demo-walkthrough.md) provides a presentation sequence and
expected results. Commands below assume a Bash/Zsh-style shell at the repository root.

## Start with Docker Compose

Install Git and Docker Desktop, or Docker Engine with the Compose plugin. Start
Docker before proceeding. The initial build needs internet access to download
the base image and Python packages. Obtain the project:

```bash
git clone https://github.com/j22868706/sideproject_fabflow.git
cd sideproject_fabflow
cp .env.example .env
# Edit .env: replace the password placeholder with a local development password.
docker compose config --quiet
docker compose up --build --wait --wait-timeout 120
docker compose ps
```

Both `api` and `dashboard` should be healthy. The PostgreSQL `db` service should
be running; check DB readiness separately with
`docker compose exec db pg_isready -U fabflow -d fabflow`. Compose explicitly sets
`FABFLOW_RUN_STORE=postgres`; completed results are written before HTTP 201 and
read from PostgreSQL. DB unavailability returns 503, while a successful lookup
with no matching ID returns 404. API readiness currently does not check DB.
See [Day 12](k8s/day12-postgres-read.md) for persistence acceptance and recovery.
Open:

| Interface | Host address |
| --- | --- |
| Dashboard | http://localhost:8501 |
| API Swagger | http://localhost:8000/docs |
| API readiness | http://localhost:8000/health/ready |

Inside the dashboard, keep **API base URL** set to `http://api:8000`.
Compose resolves `api` on the container network. Host ports are bound to
`127.0.0.1`; this configuration is for a local demonstration.

Confirm service readiness and both example API workflows:

```bash
curl --fail-with-body http://127.0.0.1:8000/health/ready
docker compose exec -T dashboard python - < scripts/smoke_containers.py
```

The readiness response is `{"status":"ready"}`. The smoke script prints `PASS`
for both presets and the dashboard/API checks. It creates two runs in the configured result store.

## Kubernetes learning deployment

The current kind manifests use PostgreSQL 17 with a 1Gi local PVC and a single
API replica. Follow [Day 13](k8s/day13-postgres-pvc.md) to create the Secret and SQL
ConfigMap, apply the DB manifests, and build/load `fabflow-api:day13`. Applying
the manifest directory alone does not create those prerequisites.

API Pod recreation has been verified against a snapshot saved outside the Pod.
PostgreSQL Pod recreation has not yet been tested. The DB is not highly available;
local kind storage does not protect against cluster deletion. Deleting the namespace
or PVC can reclaim database data under the current Delete policy.

## Start with local Python instead

Requires Python 3.12+. In a fresh checkout, create and activate a virtual environment:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev,dashboard]"
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 1
```

In a second terminal at the same repository root:

```bash
source .venv/bin/activate
python -m streamlit run app/dashboard/main.py
```

Use `http://127.0.0.1:8000` as the dashboard's API base URL. An inherited
`FABFLOW_API_URL` environment variable can override that default; the sidebar
lets you correct it. Stop each local process with Ctrl+C. Run either the local
services or the Compose stack on the default ports, so the ports do not conflict.

## Results and exports

Each **Run simulation** submission creates a unique run ID and returns after
all lots complete. The dashboard's **Load KPIs** reads that run; **Refresh KPIs**
queries it again. Settings shown next to the saved result belong to that run,
even if the form has since changed. A failed submission keeps the previous
successful result. Saved dashboard state is per browser session; reloading the
tab resets that session. Completed Compose API results remain in PostgreSQL across
API restarts; memory-mode results remain only until the API process stops.

To save API output, copy the displayed run ID and replace `RUN_ID` below:

```bash
curl --fail-with-body http://127.0.0.1:8000/api/v1/runs/RUN_ID/metrics --output /tmp/fabflow-metrics.json
curl --fail-with-body http://127.0.0.1:8000/api/v1/runs/RUN_ID/events --output /tmp/fabflow-events.json
```

There is no expiry policy or background-job queue; exports are not automatic.
`FABFLOW_RUN_STORE` accepts `memory` (default) or `postgres`; invalid values fail
startup. Compose uses PostgreSQL and the original named volume protects completed
results across API and DB container recreation. Memory-mode results disappear
on API restart, so a cached dashboard result can remain visible while refresh
returns 404. A new POST creates a different run; it is not an idempotent retry.

For a repeatable API restart check, run `prepare`, restart API, wait for healthy,
then run `verify`:

```bash
docker compose exec -T api python - prepare < scripts/check_postgres_persistence.py
docker compose restart api
docker compose ps api db
# After API is healthy:
docker compose exec -T api python - verify < scripts/check_postgres_persistence.py
```

The snapshot is stored in the API container at `/tmp/fabflow-day12-check.json`.
Use a new `--snapshot` path for repeated preparations. The snapshot survives
restart but not container recreation; see [Day 12](k8s/day12-postgres-read.md)
for the scope, manual DB outage acceptance, and the unexecuted `unavailable` mode.

## Verification and evidence

For unit/integration checks, use an activated Python environment with `.[dev,dashboard]`:

```bash
ruff check .
ruff format --check .
pytest --cov=app --cov=simulator --cov-report=term-missing
```

For real browser checks against either running stack, install optional host tools:

```bash
python -m pip install -e ".[browser]"
python -m playwright install chromium
python scripts/smoke_browser.py
```

Use `--channel chrome` for installed Google Chrome. The script exercises six
scenario/policy combinations and writes screenshots plus `trace.zip` under
`artifacts/browser/`. Open a trace with
`python -m playwright show-trace artifacts/browser/trace.zip`.
GitHub Actions runs quality, container HTTP, and Chromium checks and uploads the
`browser-acceptance` artifact. See the [verification record](day7-delivery.md).

## Troubleshooting and shutdown

| Symptom | Check or action |
| --- | --- |
| Cannot connect to Docker daemon | Start Docker Desktop/Engine, then retry `docker compose up`. |
| Port 8000 or 8501 is already allocated | Stop the other local/Compose instance using that port, then retry. |
| A service is unhealthy | Run `docker compose ps` and `docker compose logs --tail=100 api dashboard`; inspect the failing service before restarting. |
| Dashboard cannot reach API | Use `http://api:8000` for Compose, `http://127.0.0.1:8000` for local Python; select **Check connection**. |
| API is reachable but not ready | Inspect API startup logs and retry readiness after startup completes. |
| Simulation request times out | Execution may still finish server-side. No automatic retry occurs; a new submission creates a separate run. |
| KPI refresh returns 404 | The ID is absent in the configured store; memory-mode results disappear on restart. Check the backend and run ID. |
| Result queries return 503 | Check DB status and pg_isready; API readiness alone does not establish DB availability. |
| External-SSD init bind mount fails | Confirm the host path is a directory and Docker Desktop sharing covers it; Day 12 recovered after Desktop restart while preserving the named volume. |
| Swagger UI is blank | Swagger loads JavaScript/CSS from a CDN; check browser internet access or use curl. |
| Browser tools cannot find Chromium | Run `python -m playwright install chromium`, or use `--channel chrome` with installed Chrome. |

Capture logs before stopping a failing stack:

```bash
docker compose logs --no-color --tail=200
docker compose down
```

`down` removes this Compose project's containers and network. It also discards
any memory-mode API results. Compose PostgreSQL results remain in the named
volume. To start again, repeat the Compose startup command.

The PostgreSQL named volume survives ordinary `docker compose down`. Initialization
SQL runs automatically only for an empty data directory. Changing the init file
does not migrate an existing database. `docker compose down -v` deletes the DB
volume and its contents; use ordinary `down` when preserving development data.
