# Day 5: API service

## Step 1: API schemas (implemented)

`app/models/simulation.py` defines Pydantic contracts. All simulation times are minutes.

- `ScenarioCreate`: explicit process steps, machines, lots, seed, optional
  reliability and AMHS settings. Lot routes are ordered step IDs; repeated
  visits are allowed. `to_domain()` produces fresh engine inputs.
- `RunCreate`: scenario, policy (`FIFO`, `SPT`, or `CR`; default `FIFO`), and
  `normal_wait_threshold` (default 60 minutes).
- `RunResponse`: run/scenario IDs, seed, policy, aging threshold, completed
  status, simulation finish time, and completed lot count. This contract is
  for synchronous execution; it does not imply a background task lifecycle.
- `MetricsResponse`: all existing manufacturing, machine, and AMHS KPIs,
  using the engine's field names and definitions.
- `EventResponse`: manufacturing, failure/repair, and transport event fields.
  Machine events permit a null lot ID.

Unknown fields are rejected. Inputs reject blank identifiers, non-finite times,
invalid counts, due dates before arrivals, duplicate IDs, missing route steps,
missing machine groups, and invalid reliability settings. Seed and resource
counts require integers, excluding booleans. Reliability validation reuses the
domain rules. API models do not change the simulation engine.

Example `RunCreate` JSON (a small one-station scenario):

```json
{
  "scenario": {
    "scenario_id": "example",
    "seed": 42,
    "process_steps": [
      {
        "step_id": "etch",
        "name": "Etching",
        "processing_time": 2,
        "eligible_machine_group": "ETCH"
      }
    ],
    "machines": [{"machine_id": "M1", "group": "ETCH", "capacity": 1}],
    "lots": [
      {"lot_id": "L1", "arrival_time": 0, "due_date": 20, "route": ["etch"]}
    ]
  },
  "policy": "FIFO",
  "normal_wait_threshold": 60
}
```

## Step 2: synchronous run endpoints (implemented)

Start the API from the repository root after installing `.[dev]`:

```bash
source .venv/bin/activate
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Open `http://localhost:8000/docs` and submit the example above to create a run.

| Method | Path | Result |
| --- | --- | --- |
| POST | `/api/v1/runs` | Execute synchronously; return 201 and a completed run summary |
| GET | `/api/v1/runs/{run_id}` | Run summary |
| GET | `/api/v1/runs/{run_id}/metrics` | Manufacturing, machine, and transport KPIs |
| GET | `/api/v1/runs/{run_id}/events` | All events in engine order, as a JSON array |

The POST response includes a `Location` header pointing to the run summary.
Each request uses a fresh engine and a new run ID, even for identical inputs.
FIFO/SPT/CR and the aging threshold are forwarded to the engine. Results become
queryable only after execution and response conversion succeed. Unknown run IDs
return 404 with `{"detail": "Run not found"}`; request validation uses the
422 response described below.

`app/main.py` creates the application; `app/api/runs.py` contains routes;
`app/services/runs.py` executes and stores results. Synchronous route handlers
run through FastAPI's thread pool. Each application instance owns a separate
store with locked publication/lookups. Results have no automatic expiry, are
lost on restart/reload, and are not shared across processes: use one worker for
this MVP. There is no database or background job queue.

`tests/test_api_runs.py` checks all three policies against direct engine output,
including failure and transport events, repeated runs, isolated stores, and
OpenAPI routes. These HTTP checks use an in-process TestClient.

## Step 3: errors and health checks (implemented)

Validation errors return HTTP 422 with a `detail` array. Each issue contains
`loc` (field path), `msg` (reason), and `type` (validation error code). For example,
an unsupported policy identifies `["body", "policy"]`. Raw input and Pydantic
exception context are omitted, so non-finite numbers and domain validation
exceptions cannot break JSON serialization. Invalid requests never run a simulation.
Malformed JSON and missing bodies use this same response shape.

Unknown run IDs return HTTP 404 with `{"detail": "Run not found"}` across all
three query endpoints. Unexpected server errors return HTTP 500 with
`{"detail": "Internal server error"}` and log the exception server-side. Failed
execution does not publish a partial run. Error schemas are included in OpenAPI.

| Endpoint | Healthy response | Meaning |
| --- | --- | --- |
| `GET /health/live` | 200 `{"status": "alive"}` | The application can respond |
| `GET /health/ready` | 200 `{"status": "ready"}` | Startup completed and the in-memory run service exists |

Readiness is false before startup and after shutdown. An unavailable service
returns 503 `{"detail": "Service not ready"}` from readiness and run endpoints;
liveness remains independent. Readiness does not execute a simulation or promise
that every future run will succeed. There are no external database/queue dependencies
to probe in this MVP.

`tests/test_api_errors.py` covers invalid policies/scenarios, non-finite values,
malformed bodies, unknown IDs, lifecycle/readiness transitions, and unexpected
execution failures. Local validation after Step 3: 145 tests passed, Ruff lint
and formatting passed. The existing TestClient HTTPX deprecation warning remains.

## Step 4: full workflow acceptance (complete locally)

From the repository root, install and start the service:

```bash
source .venv/bin/activate
python -m pip install -e ".[dev]"
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Swagger walkthrough:

1. Open `http://localhost:8000/docs`.
2. Expand `GET /health/ready`, click **Try it out**, then **Execute**; expect
   HTTP 200 with `{"status": "ready"}`.
3. Expand `POST /api/v1/runs`, click **Try it out**, and replace the request body
   with the complete contents of [baseline.json](examples/baseline.json).
4. Click **Execute**; expect HTTP 201, `status: completed`, `completed_lots: 20`,
   and `finished_at: 175`. Copy the returned `run_id`.
5. Execute each of the three GET run endpoints with that ID. The summary matches
   the POST response; metrics report average cycle time 70.5 minutes and throughput
   approximately 6.86 lots/hour; events contain 20 `LOT_COMPLETED` records.
6. Repeat with [amhs_bottleneck.json](examples/amhs_bottleneck.json): expect
   finish time 203, average cycle time 142.75 minutes, and 40 transport jobs.
7. Change `policy` to `SPT` or `CR` to run another policy. Each POST creates a new
   ID. These examples use fixed processing times; use the Day 3 comparison command
   for the heterogeneous workload that demonstrates policy trade-offs.
8. Set `policy` to `unknown` to inspect a 422 validation response, or query a
   nonexistent run ID to inspect the 404 response.

The examples are complete API request bodies, including the outer `scenario` key.
Their routes reference IDs defined in `process_steps`. Swagger UI loads its
JavaScript/CSS from a CDN; browser internet access is needed for the interactive UI.

For a terminal workflow, in another terminal:

```bash
curl --fail-with-body -i http://127.0.0.1:8000/api/v1/runs \
  -H 'Content-Type: application/json' \
  --data-binary @docs/examples/baseline.json
# Replace RUN_ID with the ID returned above.
curl --fail-with-body http://127.0.0.1:8000/api/v1/runs/RUN_ID
curl --fail-with-body http://127.0.0.1:8000/api/v1/runs/RUN_ID/metrics
curl --fail-with-body http://127.0.0.1:8000/api/v1/runs/RUN_ID/events
```

Acceptance results:

- 150 tests passed, including 60 API model/HTTP/acceptance cases; overall
  statement/branch coverage reported by pytest-cov is 91%.
- Ruff lint and formatting passed (68 Python files).
- Tests exercise both checked-in examples end to end, concurrent requests with
  separate results, recovery after invalid input, and the Swagger/OpenAPI contract.
- A real Uvicorn server on localhost passed HTTP checks for both health endpoints,
  `/docs`, `/openapi.json`, and both example create/query/metrics/events workflows.
  The temporary server was shut down after verification. Browser interaction with
  Swagger was not automated; its HTML and OpenAPI responses were verified.
- One upstream TestClient HTTPX deprecation warning remains. Remote GitHub CI was
  not checked. Existing CI runs the new tests through the full pytest suite.

Day 5 is complete locally. Dashboard and Docker integration remain Day 6 work.
