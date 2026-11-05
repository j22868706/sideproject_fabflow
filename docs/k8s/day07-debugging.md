# Day 7: Kubernetes Troubleshooting Exercises

Status: Complete from learner terminal output, recovery/UI confirmation, and
concept review. Estimate: 3 hours; actual hours unrecorded. Change one setting
at a time and restore it before injecting another failure.

## Baseline and diagnostic approach

Verify context/namespace, node/workload state, and dashboard-to-API readiness.
The learner supplied a ready response, but not separate initial node/deployment
output. Inspect get, describe, logs, events, and actual request paths. Valid but
incorrect configuration can produce no Warning events and no application error logs.

## Failure 1: Incorrect Service targetPort

Patch live API Service targetPort to 9999 while preserving correct repository YAML.
The API listens on 8000. Dashboard-to-Service requests failed with connection
refused and exit 1 while both Pods remained 1/1 Running with zero restarts.
Service describe showed ClusterIP 10.96.124.176, port 8000, targetPort 9999,
and endpoint 10.244.0.8:9999 with no events.

Probes bypass the Service and still check Pod port 8000, so Ready did not detect
this routing error. An EndpointSlice may have ready=true with the wrong port.
Successful Pod-local HTTP helps isolate Service routing; Service port-forward is
not a substitute for an in-cluster request from another Pod.
Restore the API manifest and verify targetPort http plus dashboard-to-API readiness.
The learner confirmed successful recovery; separate raw restore-query output was
not supplied.

## Failure 2: Incorrect dashboard API URL

Override FABFLOW_API_URL with http://127.0.0.1:8000 on the live Deployment.
This replaces the dashboard Pod while leaving repository/ConfigMap correct.
The Pod printed the incorrect URL and connection refused; api:8000 from the same
Pod returned ready. Dashboard stayed Ready with zero restarts because its probes
test Streamlit:8501, not the API URL. Pod dashboard-6dc7857bdf-27hvx had IP
10.244.0.10; describe showed the incorrect environment and Normal events.
Browser sessions may retain an edited URL; inspect environment/direct HTTP and
use a fresh session for UI comparison. Handled UI errors may not appear in logs.

## Restore conflict and correction

Direct client-side apply failed because the merge retained a fixed env.value
while adding valueFrom, which Kubernetes forbids. This rejected update did not
apply; it was not a DNS or API failure. Remove FABFLOW_API_URL with set env
NAME-, then apply the original manifest, await rollout, and check URL/readiness.
Intermediate Pods may exist during these changes; inspect the final rollout.
The learner confirmed restoration of the ConfigMap reference and API access.

## Final acceptance and scope

The learner confirmed Check connection, a new baseline (FIFO, aging 60), Load KPIs,
and Refresh KPIs: 20 lots, finish 175, average cycle 70.50. Final Pods
api-9fcdd7f99-fffb6 and dashboard-5b6b6bc85c-rxb7p were 1/1 Running, zero restarts,
with ages 76m and 62s. Zero restarts on a new Pod does not mean no replacement
occurred during the exercise.

The learner correctly explained why Pod probes cannot detect a wrong Service port.
Ready reflects only the configured probe scope; it is not end-to-end validation.
No run ID, screenshot, or actual hours were supplied. Logs/events collection
commands were provided but their independent output was not received. Evidence
consists of HTTP traceback, Pod status, Service/Pod describe, and learner recovery/UI
confirmation; no assistant cluster/browser rerun occurred. Day 8 later rebuilt the
namespace and verified in-memory result loss.
References: [debug Services](https://kubernetes.io/docs/tasks/debug/debug-application/debug-service/),
[debug running Pods](https://kubernetes.io/docs/tasks/debug/debug-application/debug-running-pod/).

## Recorded commands and examples

These blocks preserve the milestone procedures and recorded output in their original
order. They describe the historical configuration; review current manifests and
prerequisites before repeating them. Resource names and IP addresses are observations,
not fixed values.

```bash
kubectl --context kind-fabflow get nodes
kubectl --context kind-fabflow -n fabflow get deployments,pods,services -o wide
kubectl --context kind-fabflow -n fabflow exec deployment/dashboard -- python -c 'import os,urllib.request; print(urllib.request.urlopen(os.environ["FABFLOW_API_URL"]+"/health/ready",timeout=5).read().decode())'
```

```bash
kubectl --context kind-fabflow -n fabflow patch service api --type=json -p='[{"op":"replace","path":"/spec/ports/0/targetPort","value":9999}]'
kubectl --context kind-fabflow -n fabflow exec deployment/dashboard -- python -c 'import os,urllib.request; print(urllib.request.urlopen(os.environ["FABFLOW_API_URL"]+"/health/ready",timeout=5).read().decode())'
```

```bash
kubectl --context kind-fabflow -n fabflow get pods
kubectl --context kind-fabflow -n fabflow describe service api
kubectl --context kind-fabflow -n fabflow get endpointslices -l kubernetes.io/service-name=api -o yaml
kubectl --context kind-fabflow -n fabflow logs deployment/api --tail=50
kubectl --context kind-fabflow -n fabflow get events --sort-by=.metadata.creationTimestamp
kubectl --context kind-fabflow -n fabflow exec deployment/api -- python -c 'import urllib.request; print(urllib.request.urlopen("http://127.0.0.1:8000/health/ready",timeout=5).read().decode())'
```

```bash
kubectl --context kind-fabflow apply -f deployments/k8s/api.yaml
kubectl --context kind-fabflow -n fabflow get service api -o yaml
kubectl --context kind-fabflow -n fabflow exec deployment/dashboard -- python -c 'import os,urllib.request; print(urllib.request.urlopen(os.environ["FABFLOW_API_URL"]+"/health/ready",timeout=5).read().decode())'
```

```bash
kubectl --context kind-fabflow -n fabflow set env deployment/dashboard FABFLOW_API_URL=http://127.0.0.1:8000
kubectl --context kind-fabflow -n fabflow rollout status deployment/dashboard --timeout=180s
kubectl --context kind-fabflow -n fabflow exec deployment/dashboard -- python -c 'import os,urllib.request; url=os.environ["FABFLOW_API_URL"]; print("API URL:",url,flush=True); print(urllib.request.urlopen(url+"/health/ready",timeout=5).read().decode())'
```

```bash
kubectl --context kind-fabflow -n fabflow get pods
kubectl --context kind-fabflow -n fabflow describe pods -l app=fabflow-dashboard
kubectl --context kind-fabflow -n fabflow get configmap dashboard-config -o yaml
kubectl --context kind-fabflow -n fabflow logs deployment/dashboard --tail=50
kubectl --context kind-fabflow -n fabflow get events --sort-by=.metadata.creationTimestamp
kubectl --context kind-fabflow -n fabflow exec deployment/dashboard -- python -c 'import urllib.request; print(urllib.request.urlopen("http://api:8000/health/ready",timeout=5).read().decode())'
```

```bash
kubectl --context kind-fabflow -n fabflow set env deployment/dashboard FABFLOW_API_URL-
kubectl --context kind-fabflow apply -f deployments/k8s/dashboard.yaml
kubectl --context kind-fabflow -n fabflow rollout status deployment/dashboard --timeout=180s
kubectl --context kind-fabflow -n fabflow exec deployment/dashboard -- python -c 'import os,urllib.request; url=os.environ["FABFLOW_API_URL"]; print("API URL:",url); print(urllib.request.urlopen(url+"/health/ready",timeout=5).read().decode())'
```

```bash
kubectl --context kind-fabflow -n fabflow get deployments,pods,services -o wide
kubectl --context kind-fabflow -n fabflow port-forward service/dashboard 18501:8501
```

```text
The Deployment "dashboard" is invalid:
spec.template.spec.containers[0].env[0].valueFrom:
Invalid value: "": may not be specified when `value` is not empty
```
