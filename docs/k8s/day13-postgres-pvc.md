# Day 13: Kubernetes PostgreSQL, PVC, and Secret

Status: Implementation, core acceptance, and conceptual review complete from learner
terminal output and workspace inspection. Progress: 13/30 (43.3%); hours unrecorded.

## Deployment

Namespace fabflow gained postgres-data PVC (1Gi, RWO, standard), PostgreSQL 17
single-replica Deployment with Recreate, and ClusterIP postgres:5432 selecting
app=fabflow-postgres. PVC mounts /var/lib/postgresql/data with PGDATA under pgdata.
DB/user are fabflow; password comes from postgres-credentials/POSTGRES_PASSWORD.
Do not print Secret contents or commit .env.

postgres-init ConfigMap supplies the existing SQL read-only at docker-entrypoint-initdb.d.
It initializes only empty data, not migrations. DB startup/readiness use pg_isready;
requests 100m/128Mi, limits 1000m/512Mi. pg_isready does not validate credentials
or schema; SQL checks are separate. API changes from day4 to day13, selects postgres,
uses PGHOST=postgres/PGPORT=5432/PGDATABASE=PGUSER=fabflow and the Secret password.

At lesson start, node and API/dashboard were Ready, each app had one restart after
Docker Desktop restart, and no PVC existed. standard used local-path provisioning,
Delete reclamation, WaitForFirstConsumer, and no expansion. PVC Pending became Bound
after a consumer Pod appeared. This uses local Docker disk, not a paid cloud disk;
PVCs in other environments may provision billable storage.

## Prerequisites and observed acceptance

An existing kind cluster/namespace/dashboard and standard StorageClass are required.
.env must contain only the intended POSTGRES_PASSWORD. create commands apply only
when resources do not exist; replacing a Secret does not rotate an existing DB
role password. Applying the manifest directory alone does not create the external
Secret/init ConfigMap. Build/load the local day13 image explicitly; it is not published.

Observed: Secret Opaque DATA=1, ConfigMap DATA=1; postgres-68b5ffb575-2k8mj
1/1 Running, zero restarts; PVC Bound to pvc-60e544b2-48ce-4579-b74c-49669e01b4a9.
SQL returned fabflow/fabflow/completed_runs, confirming initial schema creation.
Service 10.96.63.238:5432 mapped to 10.244.0.8:5432. New API
api-5ffdfc4f9-ksk42 was Ready and psycopg through Service DNS confirmed DB/user/table.
IPs are recorded observations; do not configure fixed Pod IPs.

## API Pod replacement acceptance

Real Pod-local HTTP created 1ab982bf-4c71-4051-94f2-e7f95f53dab5 with 201/Location,
12 lots, and 142 events, in the K8s DB rather than a migration from Compose.
The snapshot was copied from API /tmp/fabflow-day13-check.json to Mac
/tmp/fabflow-day13-before-pod-rebuild.json and parsed before deleting the old Pod.
Replacement api-5ffdfc4f9-w6r5t became 1/1 Running, zero restarts. Copying the external
snapshot into it and running verify passed complete summary/metrics/events,
including event ordering, plus unknown-ID 404 on all three endpoints.
The Mac snapshot is neither a committed Git artifact nor a DB backup.

## Failure boundaries and verification

The learner corrected the assumption that PostgreSQL implies cluster-deletion
survival. Current storage resides on the kind node; cluster deletion may remove it.
API replacement, DB replacement, and whole-cluster loss are different scopes.
At this point DB Pod recreation, PVC/namespace deletion, and cluster rebuild were
untested. A single DB with Recreate has downtime during replacement and no HA/backup.
Delete reclamation may destroy data after PVC deletion: do not repeat Day 8 cleanup.
DB readiness does not validate all schema; API readiness does not check DB.

No dashboard/UI, API Service/port-forward, K8s DB outage, dual-replica, performance,
recovery timing, or zero-downtime measurement occurred here. HTTP checks were local
to the API Pod. Final host Python 3.14 checks: Ruff, format 96 files, 184 tests
(one upstream warning), and diff checks passed. Three DB manifests passed server
dry run; configured output did not mean live changes. Python 3.12 built the API;
full container tests and remote CI were not rerun. Day 14 rechecks live health and
validates direct reads from two API replicas.

## Recorded commands and examples

These blocks preserve the milestone procedures and recorded output in their original
order. They describe the historical configuration; review current manifests and
prerequisites before repeating them. Resource names and IP addresses are observations,
not fixed values.

```bash
kubectl apply -f deployments/k8s/postgres-pvc.yaml
kubectl create secret generic postgres-credentials -n fabflow --from-env-file=.env
kubectl create configmap postgres-init -n fabflow \
  --from-file=001_completed_runs.sql=deployments/postgres/init/001_completed_runs.sql
kubectl apply -f deployments/k8s/postgres.yaml
kubectl rollout status deployment/postgres -n fabflow --timeout=180s
kubectl get pods,pvc -n fabflow
kubectl exec -n fabflow deployment/postgres -- \
  psql -U fabflow -d fabflow -v ON_ERROR_STOP=1 \
  -c "SELECT current_database(), current_user, to_regclass('public.completed_runs');"
kubectl apply -f deployments/k8s/postgres-service.yaml
kubectl get endpointslices -n fabflow -l kubernetes.io/service-name=postgres
docker build --target api -t fabflow-api:day13 .
kind load docker-image fabflow-api:day13 --name fabflow
kubectl apply --dry-run=server -f deployments/k8s/api.yaml
kubectl apply -f deployments/k8s/api.yaml
kubectl rollout status deployment/api -n fabflow --timeout=180s
```

```bash
kubectl exec -i -n fabflow deployment/api -- \
  python - prepare --snapshot /tmp/fabflow-day13-check.json \
  < scripts/check_postgres_persistence.py
kubectl exec -n fabflow deployment/api -- cat /tmp/fabflow-day13-check.json \
  > /tmp/fabflow-day13-before-pod-rebuild.json
```

```bash
kubectl delete pod -n fabflow api-5ffdfc4f9-ksk42
kubectl rollout status deployment/api -n fabflow --timeout=180s
kubectl get pods -n fabflow
```

```bash
kubectl exec -i -n fabflow deployment/api -- \
  python -c 'import sys; from pathlib import Path; Path("/tmp/fabflow-day13-check.json").write_bytes(sys.stdin.buffer.read())' \
  < /tmp/fabflow-day13-before-pod-rebuild.json
kubectl exec -i -n fabflow deployment/api -- \
  python - verify --snapshot /tmp/fabflow-day13-check.json \
  < scripts/check_postgres_persistence.py
```

```text
PASS: summary matches pre-restart snapshot
PASS: metrics matches pre-restart snapshot
PASS: events matches pre-restart snapshot
PASS: unknown ID returns HTTP 404 for summary
PASS: unknown ID returns HTTP 404 for metrics
PASS: unknown ID returns HTTP 404 for events
run_id: 1ab982bf-4c71-4051-94f2-e7f95f53dab5
```
