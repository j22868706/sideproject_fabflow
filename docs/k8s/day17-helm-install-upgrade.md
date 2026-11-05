# Day 17: Helm Installation and Replica Upgrades

Status: Guided configuration, fresh-namespace installation, HTTP acceptance, and
replica upgrades complete. Evidence: learner terminal output and assistant rendering.
Progress 17/30 (56.7%); actual hours unrecorded.

## Completed chart

Helm v4.3.1/chart 0.1.0 gained postgres database/username, existingSecret/passwordKey,
and persistence class/size values; passwords remain external. The chart renders
nine resources: three Deployments, three Services, two ConfigMaps, one PVC.
The Secret is created separately and not release-managed.

The release-prefixed standard PVC is 1Gi/RWO. files/001_completed_runs.sql duplicates
the existing SQL; required/Files.Get/nindent render its ConfigMap, and both copies
must match. DB mounts PVC at /var/lib/postgresql/data with PGDATA under pgdata,
and read-only init SQL. API selects postgres via release DB Service/Secret.
Dashboard ConfigMap supplies http://fabflow-api:8000 for this release.
API/dashboard have startup/readiness/liveness; DB startup/readiness use TCP
pg_isready -h 127.0.0.1, not credential/schema validation. Fixed template requests:
API 100m/128Mi, dashboard 100m/256Mi, DB 100m/128Mi; limits all 1000m/512Mi.

## Fresh installation acceptance

Initially original fabflow workloads/node were Ready with PVC Bound; fabflow-helm
was absent. New namespace and its own Opaque DATA=1 Secret were created from ignored
.env; Secrets cannot be referenced across namespaces. Nine-resource server dry run
passed. Install yielded release fabflow revision 1 deployed; both APIs/dashboard/DB
Ready, zero restarts. New PVC bound to pvc-5b243a9e-ec4c-4f0a-a87e-2650a639b1dd.
The original namespace/data remained separate; no old-result migration occurred.

API psycopg returned fabflow/fabflow/completed_runs, proving DB Service connectivity,
credentials, and empty-directory initialization. Dashboard-container HTTP smoke
passed baseline 175/70.5/0 and AMHS 203/142.75/40, plus dashboard health/HTML,
readiness, and create/query/metrics/events. This was not browser interaction.

## Replica upgrades and external snapshot

prepare created d5c0555d-4b4c-4833-9ab8-153cc6cb9f60 with 201/Location, 12 lots,
142 events. Copy /tmp/fabflow-day17-check.json outside the Pod to Mac
/tmp/fabflow-day17-before-upgrade.json and validate it before changes.
Creation/copy used Deployment exec successfully; future repeats should name one
Pod explicitly rather than assume two Deployment exec calls choose the same Pod.

Upgrade to one API replica produced revision 2 deployed; complete results and
unknown-ID 404 passed after importing the external comparison snapshot. reset-values
restored defaults/two API replicas and created revision 3; revisions 1/2 superseded.
Chart version stayed 0.1.0. Both APIs/dashboard/DB had zero restarts and the same
PVC/PV. New Pod fabflow-api-b6c874b7-xsvxg independently passed full snapshot/404 checks.
reset-values clears all overrides, not only replicas; it was appropriate only for
this all-default configuration. No image/template update or rolling update was tested.

## Checks and boundaries

Learner checks: lint one chart/zero failures (icon INFO), nine-resource server dry
run, SQL cmp, Ruff, format 101 files, 184 tests/one upstream warning, diff checks.
Assistant also read/rendered final chart. Host Python 3.14; API Python 3.12; no
full container tests or remote CI confirmation. Missing kubectl last-applied
annotation warnings are expected for Helm resources; dry run did not add annotations.
Keep raw fabflow managed with manifests and fabflow-helm with Helm.

No update-window HTTP failures, image rollout, rollback, or zero-downtime measurement.
PVC has no keep policy; uninstall/namespace deletion may remove data under
standard/Delete. Namespace deletion also removes the external Secret. No uninstall
was tested. Single local DB is not HA/backup; readiness ignores DB. Init SQL is
not migration; changing a Secret does not rotate an existing DB password.
Local day13/day5 defaults are not registry-published. Day 18 adds image CI/SHA tags.

## Recorded commands and examples

These blocks preserve the milestone procedures and recorded output in their original
order. They describe the historical configuration; review current manifests and
prerequisites before repeating them. Resource names and IP addresses are observations,
not fixed values.

```bash
helm lint deployments/helm/fabflow
kubectl create namespace fabflow-helm
kubectl create secret generic postgres-credentials -n fabflow-helm --from-env-file=.env
helm template fabflow deployments/helm/fabflow --namespace fabflow-helm \
  | kubectl apply --dry-run=server -f -
helm install fabflow deployments/helm/fabflow -n fabflow-helm --wait --timeout 5m
```

```bash
kubectl exec -i -n fabflow-helm deployment/fabflow-dashboard -- \
  python - < scripts/smoke_containers.py
```

```text
PASS: Three-stage baseline; finish=175, cycle=70.5, transport_jobs=0
PASS: AMHS bottleneck; finish=203, cycle=142.75, transport_jobs=40
PASS: dashboard health/HTML, API readiness, and both create/query/metrics/events workflows
```

```bash
helm upgrade fabflow deployments/helm/fabflow -n fabflow-helm \
  --set api.replicaCount=1 --wait --timeout 5m
```

```bash
helm upgrade fabflow deployments/helm/fabflow -n fabflow-helm \
  --reset-values --wait --timeout 5m
helm history fabflow -n fabflow-helm
kubectl get deployment,pods,pvc -n fabflow-helm
```

```text
PASS: summary matches pre-restart snapshot
PASS: metrics matches pre-restart snapshot
PASS: events matches pre-restart snapshot
PASS: unknown ID returns HTTP 404 for summary
PASS: unknown ID returns HTTP 404 for metrics
PASS: unknown ID returns HTTP 404 for events
run_id: d5c0555d-4b4c-4833-9ab8-153cc6cb9f60
```
