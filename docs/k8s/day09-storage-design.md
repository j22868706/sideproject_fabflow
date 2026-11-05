# Day 9: Result Storage Interface and PostgreSQL Design

Status: Design and guided exercises complete; no database implementation or runtime
verification at this milestone. Actual hours unrecorded. Days 10/11/12 were planned
for DB setup, writes, then reads and persistence acceptance.

## Existing contract and proposed interface

RunService owned simulation execution and a lock-protected result dictionary.
StoredRun grouped summary, metrics, and ordered events; all response conversions
completed before publishing. Keep synchronous execution and every existing HTTP
response field. Store completed results only, without running/failed job states,
background execution, checkpoints, or automatic recovery.

RunStore.save(run) returns None after commit, rejecting duplicate IDs without
overwriting. get(run_id) returns StoredRun or None only for a successful lookup
with no row. Connectivity/query/decoding failures raise storage exceptions, not
false 404s. Adapter errors are translated without exposing credentials.
MemoryRunStore retains per-process locking; PostgresRunStore shares a database.
Inject a store through create_app/RunService and never silently fall back to memory
when an explicitly selected database fails. Move StoredRun/Protocol into a separate
module to avoid circular imports. Connection pooling/lifespan cleanup was a design
idea, not implemented at this milestone or implied by this document.

## Schema and serialization

Use one completed run per row: text UUID primary key, summary/metrics JSONB objects,
events JSONB array, and created_at timestamptz. NOT NULL prevents SQL NULL; CHECK
constraints enforce JSON shapes and a non-null summary.run_id matching the key,
but do not replace full Pydantic validation. The primary-key index covers current
ID lookups; extra JSON indexes and event normalization are deferred until needed.

created_at uses database transaction-start time, distinct from finished_at in
simulation minutes. Serialize with model_dump(mode="json"), parameterized SQL,
and the driver JSON adapter; validate reads with existing response models and
restore events as a tuple. JSONB object key order is irrelevant; event array order
must remain intact, including equal-timestamp events. Do not sort events solely
by timestamp. Validate complete data/IDs and JSON-compatible values before saving.
References: [JSON types](https://www.postgresql.org/docs/18/datatype-json.html),
[transactions](https://www.postgresql.org/docs/18/tutorial-transactions.html).

## Commit and failure semantics

Validate request -> simulate -> convert all responses -> INSERT complete row ->
COMMIT -> return 201 + Location. Do not hold a database transaction during simulation.
Rollback/release the connection on failure, and never publish only a summary.

| Condition | Intended behavior |
| --- | --- |
| Invalid request | Existing 422; no simulation/write |
| Simulation/response-conversion failure | Generic 500; no saved result |
| DB unavailable | Generic 503; no 201 or memory fallback |
| Constraint, decoding, unexpected error | Generic 500; protected diagnostics |
| Successful lookup without row | Existing 404 |
| Commit succeeds but response connection fails | Complete row may exist although client did not receive success |

There is no idempotency key; retrying POST creates a new run. An ambiguous commit
cannot prove rollback or absence of data. Atomic storage means a complete row,
not that every observed client error guarantees no row. The planned storage-aware
readiness check remained future work; liveness should not cause DB outage restart
loops. Current implementation status is documented in later milestones.

## Exercises and acceptance plan

The learner completed interface types, delegation, JSON shapes, atomicity,
constraints, ID consistency, event order, retry limits, and interchangeable stores.
They corrected confusion between metrics objects/events arrays, and understood
that the store receives the complete StoredRun while get forwards the run_id.
Exercises were text/code sketches only: no DB, SQL execution, or app changes.
The initial assistant design was adjusted to the schema developed in the exercises.

Future real-DB checks: complete JSON round-trip including null/equal-time ordering,
commit before 201, unknown-ID 404 versus storage failure, restart persistence, and
direct reads by two API Pods. Mocks alone do not prove persistence. Uncommitted
visibility, duplicate IDs, and commit failures require separate verification.
A single local DB/PVC is not HA or backup; in-flight synchronous simulations can
still fail on API termination. Workbook updates for Days 8–9 were pending at this
historical point; follow the current workbook for present progress.

## Recorded commands and examples

These blocks preserve the milestone procedures and recorded output in their original
order. They describe the historical configuration; review current manifests and
prerequisites before repeating them. Resource names and IP addresses are observations,
not fixed values.

```python
class RunStore(Protocol):
    def save(self, run: StoredRun) -> None: ...
    def get(self, run_id: str) -> StoredRun | None: ...
```

```sql
CREATE TABLE completed_runs (
    run_id text PRIMARY KEY,
    summary jsonb NOT NULL CHECK (jsonb_typeof(summary) = 'object'),
    metrics jsonb NOT NULL CHECK (jsonb_typeof(metrics) = 'object'),
    events jsonb NOT NULL CHECK (jsonb_typeof(events) = 'array'),
    created_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CHECK (summary ->> 'run_id' IS NOT NULL AND summary ->> 'run_id' = run_id)
);
```

```text
Validate request -> finish simulation -> convert all responses -> save complete row
                                           → Confirm COMMIT -> HTTP 201 + Location
```

```python
def __init__(self, store: RunStore) -> None:
    self._store = store


# After simulation and response conversion in create(), replace dictionary storage:
# self._store.save(stored)


def get(self, run_id: str) -> StoredRun | None:
    return self._store.get(run_id)
```
