# Day 11: Writing Completed Results to PostgreSQL

Status: Core implementation and acceptance complete from learner terminal output
and assistant workspace review. Actual hours unrecorded; workbook dates are planned,
not completion dates.

## Implementation

run_store.py defines StoredRun, RunStore Protocol, MemoryRunStore, RunStoreError,
RunStoreUnavailable, and RunAlreadyExists. RunService receives the store and saves
only after all response conversion, returning only after save succeeds; get delegates.
PostgresRunStore.save uses one parameterized INSERT for summary/metrics/events,
Pydantic JSON serialization, and psycopg Jsonb. Connection context exit commits on
success, rolls back on exception, and closes the connection. Simulation occurs
outside the transaction; each save opens a connection, without pooling.

UniqueViolation maps to RunAlreadyExists, OperationalError to RunStoreUnavailable,
and other psycopg errors to RunStoreError. create_app(store=None) supports explicit
injection; a failing selected store never falls back. Unavailability returns generic
503 with no Location; other storage errors retain generic 500. The 503 response
and associated log do not expose underlying connection diagnostics.

## Real database and HTTP acceptance

The rebuilt Compose API was healthy and PostgreSQL 17 was running. These were real
queries/requests, not mocks, and did not expose real credentials.

1. RunService(PostgresRunStore()) ran the comparison scenario, FIFO/aging 15.
   Run 3dd70628-60ba-497c-b733-cb8f510dfbe6 had 12 completed lots/142 events.
   An independent connection compared all three committed JSON values and event order.
2. Reconstructed StoredRun was saved with PGPORT=1 only in a verification process;
   connection failure correctly raised RunStoreUnavailable.
3. A temporary threaded Uvicorn server on 127.0.0.1:8765 used explicit PostgresRunStore
   injection. Real HTTP created 6d706057-52b1-4f63-8cab-56e15edb549a with 201/Location;
   an independent DB connection saw matching summary and nonempty metrics/events.
4. The same temporary-server pattern with PGPORT=1 returned generic 503 without
   Location. finally shut down the temporary server.

The bad port affected only the docker exec verification process. The DB and normal
API process were not stopped/reconfigured. Session scripts were not yet packaged
as reusable integration-test files.

## Corrections and review

A misplaced dataclass decorator was moved from RunStoreError back to StoredRun.
The initial asdict payload retained internal lot state and produced 48 extra_forbidden
errors before simulation/save; explicitly selecting lot_id, arrival_time, due_date,
priority, and route corrected it. The learner understood exceptions prevent return,
normal save completion means commit, and a lost reply after commit can leave data.
There is no POST idempotency key or automatic retry.

Learner checks passed Ruff, format (93 files), pytest (181 passed, one upstream
Starlette TestClient/HTTPX warning), and diff checks on host Python 3.14. Real
DB/HTTP checks used the Python 3.12 API container, without a full container test
rerun. The assistant also corrected MemoryRunStore duplicate handling from
ValueError to RunAlreadyExists and ran focused checks.

## Historical limits and handoff

The normal create_app application still used MemoryRunStore; Compose/K8s had not
switched. PostgresRunStore implemented save only, lacking get, so injection was
valid only for the tested POST path, not result queries. Day 12 added reads,
backend selection, restart acceptance, and reusable scripts.

Real duplicate-ID, uncommitted visibility, commit-time failure, rollback, and volume
recreation paths were not separately tested. Connection refusal does not cover all
failure modes. Readiness did not check DB; no pooling, K8s DB/PVC, or dual-replica
acceptance existed here. Compose healthy did not establish live K8s health.
Workbook status was updated to 11/30; actual hours remained blank.

## Recorded commands and examples

These blocks preserve the milestone procedures and recorded output in their original
order. They describe the historical configuration; review current manifests and
prerequisites before repeating them. Resource names and IP addresses are observations,
not fixed values.

```text
   run_id: 3dd70628-60ba-497c-b733-cb8f510dfbe6
   completed_lots: 12
   event_count: 142
   PASS: committed summary, metrics, and events match
   ```

```text
   PASS: connection failure raises RunStoreUnavailable
   ```

```text
   run_id: 6d706057-52b1-4f63-8cab-56e15edb549a
   PASS: HTTP 201 + Location; committed result found in PostgreSQL
   ```

```text
   Result storage unavailable on /api/v1/runs
   PASS: real database connection failure returns HTTP 503
   ```

```text
ruff check .                  All checks passed!
ruff format --check .         93 files already formatted
pytest -q                     181 passed, 1 warning
git diff --check              No output
```
