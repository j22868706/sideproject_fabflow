# Day 12: PostgreSQL Reads and Persistence Acceptance

Status: Guided implementation and core acceptance complete from learner output and
workspace review. Actual hours unrecorded; planned dates are not completion dates.

## Implementation

PostgresRunStore.get uses parameterized SELECT and validates summary/metrics/events
with Pydantic, retaining event order as a tuple and checking summary ID matches
the requested ID. Only a successful empty query returns None. OperationalError
maps to unavailable/503; other psycopg or validation errors map to RunStoreError.

create_app chooses memory by default, postgres when FABFLOW_RUN_STORE=postgres,
and raises ValueError for other values. Explicit injected stores take priority;
there is no silent fallback. Compose API selects postgres with PG* connection
settings, while DB retains POSTGRES_* initialization settings. Local unconfigured
API/tests and the then-unmodified K8s deployment still used memory.
Three parameterized HTTP tests cover unavailable reads. The persistence script
provides prepare/verify/unavailable; it sends HTTP and does not restart containers.

## Real acceptance sequence

1. get loaded Day 11 run 3dd70628-60ba-497c-b733-cb8f510dfbe6: 12 lots/142 events,
   all three JSON values equal to independent SQL; unknown UUID returned None.
2. Rebuilt Compose API selected postgres. Port 8000 returned complete matching
   results; all three unknown-ID endpoints returned 404.
3. POST created d1ff784b-c208-48a9-b06e-8c8fd8b88f02 with 201/Location, 12 lots,
   142 events. Full snapshot: /tmp/fabflow-day12-before-restart.json inside API.
4. After API restart/healthy, all three responses matched the original snapshot.
5. DB stop caused all three known-ID reads to return 503 Result storage is unavailable,
   not 404. After recovery, results remained identical.
6. Recovery included DB force-recreation and Docker Desktop restart with the same
   named volume. No volume deletion or DB reinitialization occurred.
7. Reusable prepare created 77f03e37-0ac1-43f4-b0e3-2b8556693a50; after actual API
   restart, verify passed all three full comparisons and three unknown-ID 404s.

prepare/verify were executed; unavailable mode itself was not yet run. Manual outage
checks do not prove that mode's additional unknown-ID-during-outage behavior.

## Repeating acceptance safely

The default /tmp/fabflow-day12-check.json is in the API container. restart preserves
that container file; force-recreate/down removes it, so copy snapshots outside the
container before recreation. prepare refuses overwrite; use a new filename.
A real restart between prepare/verify is required to claim restart persistence.
The script alone cannot prove postgres is selected; configuration, SQL, and actual
outage provide that evidence. It creates real runs without deleting acceptance data.

## External-SSD bind-mount incident

DB startup failed before PostgreSQL execution with an OCI runtime error:
/host_mnt/Volumes/externalssd/swe/fabflow/deployments/postgres/init: not a directory.
The assistant verified the host directory/file, Compose mount, named data volume,
and read-only init bind mount. Force-recreation did not fix it. File sharing already
included /Volumes, so it was not changed. After Docker Desktop restart, docker.sock
was temporarily missing; once docker info showed Server available, DB accepted
connections, API became healthy, and complete result comparisons passed.
The mount recovered, but the exact cause was not established. This does not prove
a particular Docker Desktop bug or permission issue. Do not use down -v as a fix.

## Corrections, checks, and limits

get was moved out of save's scope; 24 API regression tests passed. Duplicate FastAPI
construction/None-store order, FABFLOW_RUN_STORE on the wrong service, overwritten
DB initialization variables, and an empty nested environment entry were corrected.
Compose syntax validation alone does not prove correct service placement.
Missing host psycopg initially blocked collection; editable development reinstall fixed it.

The learner distinguished 404 (successful lookup, no row) from 503 (cannot determine
existence), and explained named-volume survival independent of API memory.
Final host checks: 184 passed, one upstream warning; format 95 files, Ruff and diff
checks passed on Python 3.14. Real HTTP/DB used Python 3.12. No full container-test,
UI/browser, or remote CI rerun occurred.

Readiness still ignored DB; per-operation connections, no pooling/migrations/backup/HA.
The volume does not protect loss of the entire Docker VM; only committed results
are protected, not in-flight simulations. Decode corruption, duplicate DB IDs,
commit failure, and recovery timing were not tested. K8s was checked at lesson start,
but not after Docker restart. Day 13 must recheck it. Progress: 12/30 (40%).

## Recorded commands and examples

These blocks preserve the milestone procedures and recorded output in their original
order. They describe the historical configuration; review current manifests and
prerequisites before repeating them. Resource names and IP addresses are observations,
not fixed values.

```bash
docker compose exec -T api python - prepare < scripts/check_postgres_persistence.py
docker compose restart api
docker compose ps api db
# After API becomes healthy:
docker compose exec -T api python - verify < scripts/check_postgres_persistence.py
```

```bash
docker compose exec -T api python - prepare --snapshot /tmp/day12-repeat.json \
  < scripts/check_postgres_persistence.py
docker compose exec -T api python - verify --snapshot /tmp/day12-repeat.json \
  < scripts/check_postgres_persistence.py
```

```bash
docker compose up -d db
docker compose exec db pg_isready -U fabflow -d fabflow
docker compose up -d api
docker compose ps api db
```
