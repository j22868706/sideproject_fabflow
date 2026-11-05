# Day 14: Consistent Reads Across Two API Replicas

Status: Guided operations, core acceptance, and review complete from learner output
and workspace checks. Actual hours unrecorded; progress 14/30 (46.7%).

## Change and method

Raw api.yaml replicas changed from 1 to 2. Keep day13, postgres backend,
PGHOST=postgres, the Secret, single DB, and Recreate strategy. Simulation, responses,
and schema were unchanged. Create on Pod A and query A and B directly; repeated
Service requests alone do not prove that different Pods served them.

Initial assistant read-only checks found node Ready, API/dashboard/DB 1/1 Running,
1Gi RWO PVC Bound, and a clean working tree. After apply/rollout:

| Role | Pod | IP | State |
| --- | --- | --- | --- |
| A | api-5ffdfc4f9-w6r5t | 10.244.0.10 | Ready, zero restarts |
| B | api-5ffdfc4f9-sr8s4 | 10.244.0.11 | Ready, zero restarts |

Both ran on fabflow-control-plane. Names/IPs are observations; requery on repeats.
Two same-node replicas do not provide node fault tolerance or zero-downtime updates.

## Direct HTTP and database evidence

A created be4c1d60-b9d0-4ca1-9fa5-e95aae5448d1 with 201/Location, 12 lots, and
142 events. Its full snapshot was copied to Mac /tmp/fabflow-day14-snapshot.json,
then transferred to B for comparison. Both A/B returned identical summary, metrics,
and ordered events; unknown IDs returned 404 on all three endpoints. The snapshot
was an expected value, not imported into the DB or used to simulate an API reply.
The script's pre-restart label was reused; no restart was performed in this lesson.

Independent psycopg sessions using each Pod's PG* settings queried database,
server address/port, and count for that run. Both reached fabflow at
10.244.0.8:5432 with count=1. Passwords were not printed; deployment settings still
used Service DNS rather than hard-coded IPs.

## Scope and checks

The learner correctly explained that DB failure affects both APIs: replicas do not
provide DB HA, and unavailable reads should return 503 rather than 404. DB outage
was not exercised here; prior real outage evidence was Day 12 Compose.
Not tested: creation on B/read on A, concurrent POSTs, Service balancing, API fault
recovery, performance, UI/browser regression, or availability improvement. Day 13
replacement evidence remains specific to that earlier run; no Pods were deleted here.
Readiness still ignores DB; local PVC does not protect cluster deletion; no backup/HA.

Learner checks: Ruff, format (97 files), 184 tests/one upstream warning, diff checks,
and API server dry run passed. Host Python 3.14; real HTTP/SQL ran in Python 3.12
API containers. Full container tests and remote CI were not rerun. Server dry run
only validates; actual Running evidence came from apply/rollout. Day 15 validates
DB outage/recovery, old/new results, and in-flight simulation limitations.

## Recorded commands and examples

These blocks preserve the milestone procedures and recorded output in their original
order. They describe the historical configuration; review current manifests and
prerequisites before repeating them. Resource names and IP addresses are observations,
not fixed values.

```bash
kubectl apply -f deployments/k8s/api.yaml
kubectl rollout status deployment/api -n fabflow --timeout=180s
kubectl get pods -n fabflow -l app=fabflow-api -o wide
```

```bash
kubectl exec -i -n fabflow api-5ffdfc4f9-w6r5t -- \
  python - prepare --snapshot /tmp/fabflow-day14-check.json \
  < scripts/check_postgres_persistence.py
kubectl exec -n fabflow api-5ffdfc4f9-w6r5t -- \
  cat /tmp/fabflow-day14-check.json > /tmp/fabflow-day14-snapshot.json
```

```text
run_id: be4c1d60-b9d0-4ca1-9fa5-e95aae5448d1
snapshot: /tmp/fabflow-day14-check.json
PASS: HTTP 201 + Location; complete pre-restart snapshot saved
```

```bash
kubectl exec -i -n fabflow api-5ffdfc4f9-sr8s4 -- \
  python -c 'import sys; from pathlib import Path; Path("/tmp/fabflow-day14-check.json").write_bytes(sys.stdin.buffer.read())' \
  < /tmp/fabflow-day14-snapshot.json
kubectl exec -i -n fabflow api-5ffdfc4f9-sr8s4 -- \
  python - verify --snapshot /tmp/fabflow-day14-check.json \
  < scripts/check_postgres_persistence.py
kubectl exec -i -n fabflow api-5ffdfc4f9-w6r5t -- \
  python - verify --snapshot /tmp/fabflow-day14-check.json \
  < scripts/check_postgres_persistence.py
```

```text
PASS: summary matches pre-restart snapshot
PASS: metrics matches pre-restart snapshot
PASS: events matches pre-restart snapshot
PASS: unknown ID returns HTTP 404 for summary
PASS: unknown ID returns HTTP 404 for metrics
PASS: unknown ID returns HTTP 404 for events
run_id: be4c1d60-b9d0-4ca1-9fa5-e95aae5448d1
```

```sql
SELECT current_database(), inet_server_addr(), inet_server_port();
SELECT count(*) FROM completed_runs WHERE run_id = %s;
```

```text
pod: api-5ffdfc4f9-w6r5t
PGHOST: postgres
database server: ('fabflow', IPv4Address('10.244.0.8'), 5432)
PASS: shared database contains the verified run
pod: api-5ffdfc4f9-sr8s4
PGHOST: postgres
database server: ('fabflow', IPv4Address('10.244.0.8'), 5432)
PASS: shared database contains the verified run
```

```text
ruff check .                 All checks passed!
ruff format --check .        97 files already formatted
pytest -q                    184 passed, 1 warning
git diff --check             No output
API server dry run           deployment configured; service unchanged
```
