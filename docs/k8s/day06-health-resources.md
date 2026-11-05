# Day 6: Health Probes and Resource Settings

Status: Core acceptance complete from learner terminal output, UI confirmation,
and conceptual review. Estimate: 2 hours; actual hours unrecorded.

## Configuration and behavior

Add startup/readiness/liveness probes and CPU/memory requests/limits to API and
dashboard containers. Reuse day4/day5 images; no rebuild/load needed. Updating
the Pod template replaces Pods. At this milestone API Recreate interrupted service
and discarded in-memory results; dashboard replacement could reset browser sessions
and port-forward. Create fresh runs for acceptance.

kubelet sends HTTP probes to Pod IP/port without using host forwarding or the
Service. API startup/liveness use /health/live; readiness uses /health/ready,
checking lifecycle and RunService presence without running a simulation or proving
a run exists. Dashboard probes use /_stcore/health and test Streamlit itself,
not downstream API connectivity; an API outage should remain visible as a UI error.

| Probe | Period (s) | Timeout (s) | Failure threshold | Effect of sustained failure |
| --- | ---: | ---: | ---: | --- |
| Startup | 2 | 2 | 60 | Restart container; readiness/liveness wait for startup success |
| Readiness | 5 | 2 | 3 | Remove from normal new Service traffic; no restart |
| Liveness | 10 | 3 | 6 | Restart container under its restart policy |

Startup allowance is approximately 120 seconds, not an exact countdown; scheduling
and request duration affect timing. Default successThreshold is 1.

| Container | CPU request/limit | Memory request/limit |
| --- | --- | --- |
| API | 100m / 1000m | 128Mi / 512Mi |
| Dashboard | 100m / 1000m | 256Mi / 512Mi |

100m is 0.1 CPU, 1000m is 1 CPU, and Mi uses binary units. Requests guide scheduling
and CPU weighting, not instantaneous usage. CPU limits throttle; memory limits can
lead to OOM termination. Total requests are 200m/384Mi plus cluster/other workloads.
These initial local settings were not load-tuned, and limits do not expire saved
results. Inspect events, termination reason, and previous logs before adjusting.

## Observed acceptance

API api-9fcdd7f99-fffb6 (10.244.0.8) and dashboard-5b6b6bc85c-kt5rk
(10.244.0.9) became 1/1 Running. describe confirmed probes/resources, Ready True,
Normal events, cached images, and Burstable QoS; CPU limit 1 equals 1000m.
Pod start times indicate October 30, 2026, offset -0500.

In-Pod HTTP returned ready and ok. The learner confirmed connection, a fresh
baseline (FIFO, aging 60), and KPI load/refresh: 20 lots, finish 175 minutes,
average cycle 70.50. Later Pod ages were 3m30s/2m34s, both zero restarts.
This is a bounded observation, not a long-term stability or load test.
EndpointSlice commands were provided but output was not supplied; direct endpoint
readiness inspection is not claimed. No run ID, screenshots, or forwarder-stop
confirmation was supplied. The assistant did not repeat cluster/browser operations.

## Troubleshooting and handoff

For Pending, inspect insufficient CPU/memory events. For probe failures, compare
path/port and logs. For restart history, inspect Last State/Reason and logs --previous.
An isolated startup event is not proof of persistent failure. The learner correctly
explained readiness versus liveness and requests versus limits. Deliberate failures
were deferred to Day 7; preserve workloads after stopping forwarding.
References: [probes](https://kubernetes.io/docs/tasks/configure-pod-container/configure-liveness-readiness-startup-probes/),
[resource management](https://kubernetes.io/docs/concepts/configuration/manage-resources-containers/).

## Recorded commands and examples

These blocks preserve the milestone procedures and recorded output in their original
order. They describe the historical configuration; review current manifests and
prerequisites before repeating them. Resource names and IP addresses are observations,
not fixed values.

```bash
kubectl --context kind-fabflow get nodes
kubectl --context kind-fabflow -n fabflow get deployments,pods,services -o wide
```

```bash
kubectl --context kind-fabflow apply -f deployments/k8s/api.yaml
kubectl --context kind-fabflow -n fabflow rollout status deployment/api --timeout=180s
kubectl --context kind-fabflow apply -f deployments/k8s/dashboard.yaml
kubectl --context kind-fabflow -n fabflow rollout status deployment/dashboard --timeout=180s
kubectl --context kind-fabflow -n fabflow get deployments,pods -o wide
kubectl --context kind-fabflow -n fabflow describe pods -l app=fabflow-api
kubectl --context kind-fabflow -n fabflow describe pods -l app=fabflow-dashboard
```

```bash
kubectl --context kind-fabflow -n fabflow get endpointslices -l kubernetes.io/service-name=api -o yaml
kubectl --context kind-fabflow -n fabflow get endpointslices -l kubernetes.io/service-name=dashboard -o yaml
kubectl --context kind-fabflow -n fabflow exec deployment/dashboard -- python -c 'import os,urllib.request; print(urllib.request.urlopen(os.environ["FABFLOW_API_URL"]+"/health/ready",timeout=5).read().decode()); print(urllib.request.urlopen("http://127.0.0.1:8501/_stcore/health",timeout=5).read().decode())'
kubectl --context kind-fabflow -n fabflow port-forward service/dashboard 18501:8501
```

```bash
kubectl --context kind-fabflow -n fabflow get events --sort-by=.metadata.creationTimestamp
kubectl --context kind-fabflow -n fabflow logs deployment/api --tail=100
kubectl --context kind-fabflow -n fabflow logs deployment/dashboard --tail=100
```
