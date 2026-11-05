# Day 15: Persistence Acceptance and Database Outage

Status: Core failure/recovery acceptance and conceptual review complete. Operations
came from learner terminal output; the assistant independently reran final checks
and read live status. Progress 15/30 (50%); actual hours unrecorded.

## Scope and baseline

Reuse Day 14's two APIs and DB; retain PVC, namespace, and cluster. No new storage
behavior was added. The script gained unavailable-create and comparison_payload().
Each failed POST gets a unique scenario marker saved with exclusive file creation
before submission; repeat runs require a new snapshot filename. The script is sent
through stdin, so no image rebuild is required. It verifies 503, generic JSON,
and no Location. Day 14 workspace changes were preserved without a new push.

Baseline A: api-5ffdfc4f9-w6r5t; B: api-5ffdfc4f9-sr8s4; DB:
postgres-68b5ffb575-2k8mj. postgres-data was Bound to
pvc-60e544b2-48ce-4579-b74c-49669e01b4a9 (1Gi/RWO). Both APIs passed full comparison
for be4c1d60-b9d0-4ca1-9fa5-e95aae5448d1 and three unknown-ID 404 checks, using
/tmp/fabflow-day14-check.json in each Pod.

## Outage evidence

Scale DB to zero and await Pod deletion, retaining PVC Bound. Unlike deleting just
a Pod, scaling prevents automatic replacement; the manifest still declares one
replica for normal operation. Deployment became 0/0.
Both APIs ran unavailable against known/unknown IDs and all three read endpoints:
12 checks passed, each returning 503 Result storage is unavailable, never false 404.
This was unavailable mode's first real K8s outage acceptance.

Both APIs then submitted valid comparison simulations; save failed with POST 503,
generic JSON, and no Location. Recorded markers:

| API | Scenario marker |
| --- | --- |
| A | outage-6b84ef40-b6bb-4133-af98-5bf9e12a073e |
| B | outage-034b7724-a0f5-4b86-9d73-e6999575ab39 |

Each attempt record remained in its Pod at /tmp/fabflow-day15-failed-post.json.
The simulations were valid; failure occurred at result persistence.

## Recovery and data checks

Scale DB to one: replacement postgres-68b5ffb575-slbvt became Ready using the same
PVC/PV. API Pods did not restart. Both APIs again returned complete unchanged old
results and unknown-ID 404s. This added real DB Pod replacement/PVC reuse evidence.
Parameterized SQL for each failed marker found zero rows, limited to these two
connection-failed requests, not every possible failure. B then created
32a2a591-91eb-4225-8e98-21b52809e53b with 201/Location, complete readable results,
12 lots/142 events. This new run was not independently compared through A.

## Integrity and execution boundaries

All response conversion precedes a one-row INSERT, and save returns after commit.
This exercise verifies retained complete results, two no-row connection failures,
and successful recovery writes. It does not test interrupted commit, partial INSERT,
corruption, uncommitted visibility, or the real duplicate-ID branch.

The learner understood interrupted simulations cannot resume, but initially thought
replacement Pods rerun automatically. Correction: progress is process memory, no
checkpoint/queue/replay exists; only a fresh POST reruns with a new ID. A lost reply
after commit can leave data, and no idempotency key prevents duplicate submissions.
Mid-simulation termination was discussed, not exercised.

## Final verification and limits

Assistant reruns passed Ruff, formatting (98 files), 184 tests/one upstream
TestClient/HTTPX warning, diff checks, and all raw manifests' server dry run on
host Python 3.14. HTTP/DB acceptance used Python 3.12 API containers, without full
container tests, UI/browser reruns, or remote CI confirmation. Final read-only
status: both APIs and new DB Ready with zero restarts, dashboard Ready with its
existing one restart, original PVC Bound. Dry run did not repair/apply resources.

Single-node kind, single DB, Recreate downtime risk, DB-blind API readiness, and
no backups/HA remain. No recovery timing, throughput, node tolerance, or zero-downtime
claim. Day 16 creates a Helm skeleton after checking current files/state.

## Recorded commands and examples

These blocks preserve the milestone procedures and recorded output in their original
order. They describe the historical configuration; review current manifests and
prerequisites before repeating them. Resource names and IP addresses are observations,
not fixed values.

```bash
kubectl scale deployment/postgres -n fabflow --replicas=0
kubectl wait --for=delete pod -n fabflow -l app=fabflow-postgres --timeout=120s
kubectl get deployment postgres -n fabflow
kubectl get pvc postgres-data -n fabflow
```

```bash
for api_pod in api-5ffdfc4f9-w6r5t api-5ffdfc4f9-sr8s4; do
  kubectl exec -i -n fabflow "$api_pod" -- \
    python - unavailable --snapshot /tmp/fabflow-day14-check.json \
    < scripts/check_postgres_persistence.py
done
```

```bash
for api_pod in api-5ffdfc4f9-w6r5t api-5ffdfc4f9-sr8s4; do
  kubectl exec -i -n fabflow "$api_pod" -- \
    python - unavailable-create --snapshot /tmp/fabflow-day15-failed-post.json \
    < scripts/check_postgres_persistence.py
done
```

```bash
kubectl scale deployment/postgres -n fabflow --replicas=1
kubectl rollout status deployment/postgres -n fabflow --timeout=180s
kubectl get pods,pvc -n fabflow
```

```sql
SELECT count(*) FROM completed_runs WHERE summary ->> 'scenario_id' = %s;
```

```bash
kubectl exec -i -n fabflow api-5ffdfc4f9-sr8s4 -- \
  python - prepare --snapshot /tmp/fabflow-day15-recovery.json \
  < scripts/check_postgres_persistence.py
```

```text
ruff check .                         All checks passed!
ruff format --check .                98 files already formatted
pytest -q                            184 passed, 1 warning
git diff --check                     No output
kubectl apply --dry-run=server ...    All manifests passed
```
