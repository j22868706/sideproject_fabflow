# Day 8: Namespace Rebuild and In-Memory Result Loss

Status: Core operational acceptance complete from learner terminal output and UI
confirmation; actual hours unrecorded. Service DNS versus label selection was
clarified after the learner's explanation.

## Historical scope and safety boundary

This milestone deleted/recreated namespace fabflow in kind-fabflow and reapplied
API/dashboard YAML. The cluster and cached day4/day5 images were retained, so
this was not a rebuild from an empty node. It preceded PostgreSQL deployment.
Do not repeat namespace deletion against the current persistent deployment without
a backup/recovery plan: it may reclaim database storage.

## Before and after

The assistant's initial read-only check found the node Ready, both Deployments 1/1,
and Pods Running with zero restarts. The learner created baseline run
70a9bf85-0d8a-47d4-90ca-c12f628ea443, FIFO/aging 60: 20 lots, finish 175,
average cycle 70.50 minutes. Old forwarding was stopped before namespace rebuild.

| Recreated resource | Observed state |
| --- | --- |
| API | Deployment 1/1, fabflow-api:day4; Pod api-9fcdd7f99-xl2j2, 10.244.0.13, zero restarts |
| Dashboard | Deployment 1/1, fabflow-dashboard:day5; Pod dashboard-5b6b6bc85c-4f5bd, 10.244.0.14, zero restarts |
| Services | API 10.96.14.134:8000; dashboard 10.96.112.81:8501 |

From dashboard, readiness returned 200 while the old run returned 404 Run not found.
The application recovered, but the old process dictionary was gone; YAML does not
restore application data. No persistence was added here.
After restarting dashboard forwarding, the learner confirmed connection, a fresh
baseline, KPI load/refresh, and expected values. New run:
3a948935-c040-4404-96af-4fa075395b5b. Both new Pods remained Ready with zero restarts.
Screenshots, actual hours, and forwarding shutdown confirmation were not supplied.

## Service path clarification and follow-up

The actual selector is app=fabflow-api, not an image tag. api is a Service DNS name;
DNS resolves the current ClusterIP, while selector/EndpointSlice identifies backend
Pods. Recreating a Service under the same name can change ClusterIP without
requiring the dashboard URL http://api:8000 to change.

On October 31 the assistant independently rechecked the same named Pods and node:
Ready, both Deployments 1/1, zero restarts; no settings changed. Dashboard environment
was FABFLOW_API_URL=http://api:8000, DNS 10.96.14.134, readiness 200. Service selector
matched app=fabflow-api and EndpointSlice api-cz4l9 pointed to 10.244.0.13:8000,
the current API Pod. No new simulation/UI acceptance was performed in this check.

The rebuild and UI evidence came from the learner; the assistant did not delete or
recreate the namespace. The original workbook, now named
FabFlow_K8s_30_Day_Progress.xlsx, established Day 9 as storage interface/schema
design. An earlier inference from Markdown alone that no next lesson existed was
corrected against that workbook. See [Day 9](day09-storage-design.md).

## Recorded commands and examples

These blocks preserve the milestone procedures and recorded output in their original
order. They describe the historical configuration; review current manifests and
prerequisites before repeating them. Resource names and IP addresses are observations,
not fixed values.

```bash
kubectl --context kind-fabflow delete namespace fabflow --wait=true --timeout=180s
kubectl --context kind-fabflow create namespace fabflow
kubectl --context kind-fabflow apply -f deployments/k8s/api.yaml
kubectl --context kind-fabflow -n fabflow rollout status deployment/api --timeout=180s
kubectl --context kind-fabflow apply -f deployments/k8s/dashboard.yaml
kubectl --context kind-fabflow -n fabflow rollout status deployment/dashboard --timeout=180s
kubectl --context kind-fabflow -n fabflow get deployments,pods,services -o wide
```

```text
/health/ready 200 {"status":"ready"}
/api/v1/runs/70a9bf85-0d8a-47d4-90ca-c12f628ea443 404 {"detail":"Run not found"}
```

```bash
kubectl --context kind-fabflow -n fabflow port-forward service/dashboard 18501:8501
```

```text
FABFLOW_API_URL=http://api:8000
api DNS=10.96.14.134
readiness=200 {"status":"ready"}
```

```text
Service api: ClusterIP 10.96.14.134, selector app=fabflow-api
EndpointSlice api-cz4l9: 10.244.0.13:8000
API Pod api-9fcdd7f99-xl2j2: 10.244.0.13
```
