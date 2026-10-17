# Day 6: dashboard and container integration

## Step 1: dashboard entry point (implemented)

Install the dashboard dependencies from the repository root:

```bash
python -m pip install -e ".[dev,dashboard]"
```

Start the API in one terminal and the dashboard in another:

```bash
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

```bash
python -m streamlit run app/dashboard/main.py
```

Open http://localhost:8501. The sidebar accepts the API base URL; its default
is `http://127.0.0.1:8000`, or the `FABFLOW_API_URL` environment variable when set.
The address must be reachable from the dashboard server. Select **Check connection**
to call `GET /health/ready` with a five-second timeout. The page distinguishes
ready, unavailable, invalid responses, HTTP errors, and connection/timeout errors.
Connection checks run only when requested; they do not create simulations.

Docker Compose and real browser acceptance are complete locally; see Steps 4–5 below.
The dashboard communicates with the API over HTTP; simulation behavior stays in
the existing backend.

Step 1 validation on Python 3.14.6: Ruff lint and formatting passed; all 158
tests passed. Eight dashboard tests use Streamlit's AppTest to exercise initial
rendering, environment configuration, readiness responses, connection failures,
timeouts, and invalid addresses. These checks simulate HTTP responses; a live
browser/API integration check remains pending. CI installs the dashboard extra
so these tests also run on Python 3.12; remote CI has not been verified.

## Step 2: simulation controls and completion summary (implemented)

Under **Run a simulation**, select **Three-stage baseline** or **AMHS bottleneck**,
choose FIFO, SPT, or CR, and set a positive Normal lot aging threshold in minutes
(default 60). Select **Run simulation** to submit one synchronous
`POST /api/v1/runs` request. The two presets reuse existing scenario factories
and match the documented API examples. Their fixed processing times may yield
identical results across policies; they are workflow examples rather than a
policy comparison experiment.

The completed summary displays the run ID, scenario, policy, aging threshold,
seed, completed lot count, and simulated finish time. It remains visible across
widget reruns without resubmitting. It is labelled as the last successful run,
even when current settings change or a later submission fails. Changing the API
address hides results from the previous server. Browser sessions keep separate
summaries; reloading the browser clears the dashboard session.

Requests have a 60-second timeout and are never automatically retried. A timeout
does not prove server execution stopped; resubmitting creates another run. HTTP
errors are shown, including API validation details for 422 responses. Invalid
responses do not replace the last successful summary.

Step 2 validation on Python 3.14.6: Ruff lint and formatting passed; all 171 tests
passed. Dashboard tests submit both scenarios with all three policies through
the actual FastAPI application using TestClient, check finish times and queryable
run IDs, verify preset/example parity, and cover reruns, API address changes,
timeouts, errors, and retention of a previous successful result. HTTP transport
is bridged in-process; live browser/network integration remains pending.

## Step 3: KPI queries and charts (implemented)

After completing a simulation, select **Load KPIs** to query that run's
`GET /api/v1/runs/{run_id}/metrics`. The dashboard shows average/P95 cycle time,
throughput, on-time delivery, WIP, queue depth, queue waiting time, and tardiness.
Equipment charts show utilization and availability as separate percentage
charts, with a table including downtime. AMHS runs show transport job count,
vehicle utilization, and average waiting/travel minutes per transport job.
Runs without transport jobs display an explicit not-applicable message.

All values come from the API; the dashboard does not recalculate KPIs. Time units
and the observation window are displayed. Chart tooltips and accompanying tables
support inspection of values. Metrics are validated against the response schema
and the completed summary's lot count and finish time before being saved.

**Refresh KPIs** queries the same run again with a ten-second timeout. Widget
reruns reuse the saved metrics without another request. A new successful
simulation clears the previous run's KPIs; changing API addresses hides the
previous server's results. Query failures preserve the completed summary and any
saved KPIs, labelled as saved results. A 404 explains that restarting the API
clears process-local runs. No failed read creates or reruns a simulation.

Step 3 validation on Python 3.14.6: Ruff lint and formatting passed; all 179 tests
passed. Tests verify both scenarios against actual API results, percentage and
throughput formatting, equipment and AMHS chart/table data, cached reruns,
refresh errors, new-run isolation, invalid/mismatched metrics, and HTTP/network
failures. AppTest renders the charts; live browser/network and container
acceptance remain pending.

## Step 4: Docker Compose integration (implemented and validated locally)

Install and start Docker Desktop (or Docker Engine with the Compose plugin).
From the repository root:

```bash
docker compose config --quiet
docker compose up --build --wait --wait-timeout 120
```

Open the dashboard at http://localhost:8501 and the API documentation at
http://localhost:8000/docs. The first build downloads the Python base image and
dependencies. Both published ports bind to `127.0.0.1` for local use.

The Dockerfile provides separate `api` and `dashboard` targets on Python 3.12.
Both services run as a non-root user; the API installs core dependencies and
explicitly uses one Uvicorn worker. The dashboard installs the dashboard extra,
listens on all container interfaces, and disables usage telemetry. The build
context includes only the Dockerfile, package metadata, and application/simulator
sources, excluding local environments, credentials, Git history, and caches.

The dashboard uses `FABFLOW_API_URL=http://api:8000` on Compose's internal network.
Keep that address in the sidebar when using containers: `localhost` inside the
dashboard container refers to that container. API readiness and Streamlit's
`/_stcore/health` are checked separately. The dashboard starts only after API
readiness succeeds, using Compose's documented
[`service_healthy` dependency](https://docs.docker.com/compose/how-tos/startup-order/).

Run the repeatable HTTP acceptance check from the dashboard container:

```bash
docker compose exec -T dashboard python - < scripts/smoke_containers.py
```

This verifies dashboard health and HTML, API readiness, and creation, summary,
metrics, and event queries for both presets over the actual container network.
It creates two in-memory simulation runs. CI now builds the same stack and runs
this check in a separate job, with logs on failure and cleanup after each run.

Inspect and stop the stack:

```bash
docker compose ps
docker compose logs --tail=100
docker compose down
```

Stopping/restarting/recreating the API loses its in-memory runs. No persistent
storage is introduced. If startup fails, check Docker is running and ports 8000
and 8501 are free; inspect the service logs before retrying.

Local validation: Compose configuration passed, both Python 3.12 images built,
and both services became healthy. Container-network acceptance passed with
baseline finish/cycle values of 175/70.5 and AMHS values of 203/142.75, including
40 AMHS jobs and 20 lot-completion events per run. Ruff lint/format checks and all
179 local tests on Python 3.14.6 passed. The temporary `fabflow-day6-check` stack
was removed after verification. Remote CI and interactive browser acceptance
have not been verified; browser acceptance is the next step.

## Step 5: real browser acceptance (complete locally)

Start the Compose stack as described above. Install the optional browser tools
on the host and download Chromium:

```bash
python -m pip install -e ".[browser]"
python -m playwright install chromium
python scripts/smoke_browser.py
```

To use an existing Google Chrome installation instead of downloading Chromium:

```bash
python scripts/smoke_browser.py --channel chrome
```

The script uses Playwright to click actual widgets in the running Streamlit
page. It verifies readiness, both scenarios with FIFO/SPT/CR, a 30-minute aging
threshold, unique run IDs, completion summaries, API-recorded settings, cycle
time and throughput values, rendered equipment/AMHS charts, KPI refresh, saved
results, API-address isolation, and recovery after an invalid address. It also
checks for uncaught browser JavaScript errors and Streamlit exception panels.
The backend calls are real HTTP requests to the Compose API, with no mocks.

`--url` and `--api-url` override the browser-facing dashboard and API addresses.
The sidebar retains its container-network API address. Screenshots and a
Playwright trace are written to `artifacts/browser/` (ignored by Git). On failure,
`failure.png` is saved. Inspect a trace with:

```bash
python -m playwright show-trace artifacts/browser/trace.zip
```

CI runs this browser script with Chromium after the container HTTP smoke check
and uploads screenshots/traces as the `browser-acceptance` artifact.

Local acceptance passed using Playwright 1.64.0 with headless Google Chrome
155.0.8059.80 at a 1440 × 1100 viewport against the Python 3.12 Docker stack.
All six scenario/policy combinations completed. Baseline average cycle time
was 70.50 minutes and throughput 6.86 lots/hour; AMHS values were 142.75 and
5.91, with 40 transport jobs. Each submission produced a distinct, queryable run
whose recorded policy and 30-minute aging threshold matched the browser inputs.
KPI refresh, saved-result restoration, API-address isolation, and invalid-address
recovery passed. No uncaught JavaScript errors or Streamlit exception panels
were detected. KPI and chart screenshots were visually inspected for units,
legibility, and chart rendering. This validates desktop Chrome; mobile layouts
and other browser engines have not been tested.

Browser acceptance found and fixed a UI issue: after loading KPIs, the action
button retained its old **Load KPIs** label until another rerun. Successful loads
now rerun the page immediately, exposing **Refresh KPIs** without an extra user
action or additional API request. AppTest assertions guard the immediate label
change. Ruff lint/format checks and all 179 tests passed on Python 3.14.6.

Day 6 is complete locally. The temporary verification stack was stopped and
removed; screenshots and the successful trace remain in `artifacts/browser/`.
Remote GitHub CI has not been verified. Day 7 final verification, delivery
documentation, and portfolio materials remain pending.
