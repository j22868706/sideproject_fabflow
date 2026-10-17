# FabFlow operation and handoff

FabFlow runs a synthetic, finite semiconductor workload through Lithography,
Etching, and Inspection. The dashboard calls the synchronous FastAPI service;
the API owns simulation execution and process-local results. Use one API worker.
The [demo walkthrough](demo-walkthrough.md) provides a presentation sequence and
expected results. Commands below assume a Bash/Zsh-style shell at the repository root.

## Start with Docker Compose

Install Git and Docker Desktop, or Docker Engine with the Compose plugin. Start
Docker before proceeding. The initial build needs internet access to download
the base image and Python packages. Obtain the project:

```bash
git clone https://github.com/j22868706/sideproject_fabflow.git
cd sideproject_fabflow
docker compose config --quiet
docker compose up --build --wait --wait-timeout 120
docker compose ps
```

Both `api` and `dashboard` should be healthy. Open:

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
for both presets and the dashboard/API checks. It creates two in-memory runs.

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
tab resets that session. API results remain available until the API process stops.

To save API output, copy the displayed run ID and replace `RUN_ID` below:

```bash
curl --fail-with-body http://127.0.0.1:8000/api/v1/runs/RUN_ID/metrics --output /tmp/fabflow-metrics.json
curl --fail-with-body http://127.0.0.1:8000/api/v1/runs/RUN_ID/events --output /tmp/fabflow-events.json
```

There is no database, expiry policy, or background-job queue. Restarting or
recreating the API clears every stored run; exports are not automatic. A cached
dashboard result can still be visible after an API restart, but refreshing it
returns 404. Submit a new simulation to obtain a new server-side result.

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
| KPI refresh returns 404 | The run is absent, commonly after API restart. Run a new simulation. |
| Swagger UI is blank | Swagger loads JavaScript/CSS from a CDN; check browser internet access or use curl. |
| Browser tools cannot find Chromium | Run `python -m playwright install chromium`, or use `--channel chrome` with installed Chrome. |

Capture logs before stopping a failing stack:

```bash
docker compose logs --no-color --tail=200
docker compose down
```

`down` removes this Compose project's containers and network. It also discards
the API's in-memory results. To start again, repeat the Compose startup command.
