# Day 5: Dashboard Deployment and Service Connectivity

Status: Complete from learner terminal output, UI confirmation, and Service-DNS
review. Estimate: 3 hours; actual hours, run IDs, and screenshots unrecorded.

## Request path and configuration

Browser -> localhost:18501 port-forward -> Streamlit Pod:8501 -> Python HTTP
request to api:8000 -> API Service -> API Pod:8000 -> synchronous simulation and
in-memory results. Dashboard localhost refers to the dashboard Pod, not the Mac
or API. The browser does not need to call the API directly.

The [dashboard manifest](../../deployments/k8s/dashboard.yaml) adds ConfigMap
dashboard-config, Deployment dashboard, and ClusterIP Service dashboard.
The ConfigMap supplies FABFLOW_API_URL=http://api:8000 through configMapKeyRef.
Its DATA 1 means one configuration key, not one Pod. A shared image can use
different deployment settings without rebuilding. Environment variables already
in a running process do not update with ConfigMap changes: replace the Pod and
use a fresh browser session to check defaults.

Build target dashboard installs the dashboard extras, including Streamlit/httpx,
and runs on 0.0.0.0:8501. Build/load/manifest tags must match. CACHED layers and
kind's not-yet-present/loading messages are normal. No API code/image changed.
Kubernetes does not apply Compose depends_on. Rollout success without probes
was not sufficient evidence of API connectivity.

## Verification

First verify node/API availability; keep API single-replica at this milestone.
From dashboard Python, check injected URL, resolve api, and call /health/ready.
Within a namespace, api is Service DNS; across namespaces api.fabflow can be used.
DNS resolves the Service address, while the selector matches backend Pod labels.
This in-cluster test does not depend on an API port-forward on the Mac.
exec runs an extra Python process without stopping Streamlit.

Observed API URL: http://api:8000; DNS: 10.96.124.176; readiness:
{"status":"ready"}. Dashboard image fabflow-dashboard:day5 built/loaded and
rollout succeeded. Pod dashboard-78f4745f-5jdlh was 1/1 Running, zero restarts.
Both Deployments were 1/1; API Service was 10.96.124.176:8000 and Dashboard Service
10.96.66.94:8501. These addresses must not be hard-coded for rebuilds.

## UI acceptance

Open localhost:18501 with API base URL http://api:8000. Use Check connection,
Run simulation, Load KPIs, and Refresh KPIs for each preset, FIFO and aging 60.

| Scenario | Lots | Finish (min) | Average cycle (min) | Transport jobs |
| --- | ---: | ---: | ---: | ---: |
| Three-stage baseline | 20 | 175 | 70.50 | 0 |
| AMHS bottleneck | 20 | 203 | 142.75 | 40 |

The learner confirmed both workflows and refresh against these values. The
assistant did not operate the browser; no run IDs or screenshots were supplied.
Check connection calls readiness, POST runs a fresh synchronous simulation,
and KPI GET reads existing results. Cached dashboard display does not imply
results remain queryable after an API restart.

## Troubleshooting and handoff

Compare image tags/load targets, ConfigMap references, Pod readiness, Service
selector, EndpointSlice, and DNS. Reset any manually edited UI URL to api:8000.
No operational error was reported. The learner explained that api refers to the
Service; the distinction from Pod-local localhost was clarified.

Ctrl+C stops forwarding without removing workloads or ConfigMap. Shutdown was
not confirmed. Preserve the cluster for Day 6 probes and resource requests/limits.
Reference: [ConfigMap environment variables](https://kubernetes.io/docs/tasks/configure-pod-container/configure-pod-configmap/).

## Recorded commands and examples

These blocks preserve the milestone procedures and recorded output in their original
order. They describe the historical configuration; review current manifests and
prerequisites before repeating them. Resource names and IP addresses are observations,
not fixed values.

```text
Mac browser http://127.0.0.1:18501
          ↓ kubectl port-forward
Dashboard Pod: Streamlit 8501
          ↓ Python HTTP request http://api:8000
API Service → API Pod: Uvicorn 8000
          ↓
Synchronous simulation and in-memory results
```

```bash
kubectl --context kind-fabflow get nodes
kubectl --context kind-fabflow -n fabflow get deployments,pods,services -o wide
```

```bash
docker build --target dashboard -t fabflow-dashboard:day5 .
kind load docker-image fabflow-dashboard:day5 --name fabflow
```

```bash
kubectl --context kind-fabflow apply -f deployments/k8s/dashboard.yaml
kubectl --context kind-fabflow -n fabflow rollout status deployment/dashboard --timeout=120s
kubectl --context kind-fabflow -n fabflow get deployments,pods,services,configmaps
```

```bash
kubectl --context kind-fabflow -n fabflow exec deployment/dashboard -- python -c 'import os,socket,urllib.request; url=os.environ["FABFLOW_API_URL"]; print("API URL:",url); print("api DNS:",socket.gethostbyname("api")); print(urllib.request.urlopen(url+"/health/ready",timeout=5).read().decode())'
```

```bash
kubectl --context kind-fabflow -n fabflow port-forward service/dashboard 18501:8501
```

```bash
kubectl --context kind-fabflow -n fabflow describe pods -l app=fabflow-dashboard
kubectl --context kind-fabflow -n fabflow logs deployment/dashboard --tail=100
kubectl --context kind-fabflow -n fabflow logs deployment/api --tail=100
kubectl --context kind-fabflow -n fabflow get endpointslices -l kubernetes.io/service-name=api
kubectl --context kind-fabflow -n fabflow get configmap dashboard-config -o yaml
```

```text
API URL: http://api:8000
api DNS: 10.96.124.176
{"status":"ready"}
```
