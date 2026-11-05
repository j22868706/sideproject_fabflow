# Day 4: Deploying the API

Status: Core acceptance complete from learner terminal output and a Swagger
screenshot. Estimate: 3 hours; actual hours unrecorded. Actual study date:
October 30, 2026; the workbook retained its planned November 1 date.

## Deployment design

Deploy fabflow-api:day4 to kind-fabflow/fabflow, then use local port 18000 to reach
readiness and Swagger. Dashboard, probes, and resource settings were later lessons.
See [api.yaml](../../deployments/k8s/api.yaml); the file has evolved since this milestone.

At Day 4 the API used one Pod, one Uvicorn worker, in-memory results, and Recreate.
Recreate stopped the old process before starting the new one, interrupting service
and losing results. Multiple workers would have separate dictionaries.
Deployment manages ReplicaSets and desired Pod count; deleting a managed Pod
creates a replacement without restoring its old memory.

## Image and manifest mechanics

Run from the repository root. Verify Docker context desktop-linux, cluster
fabflow, node Ready, and namespace fabflow. Build target api selects the Dockerfile
API stage; `.` supplies the COPY build context. Tags must match build, load, and
Deployment. Cached build layers avoid redundant dependency installation.

The Dockerfile used Python 3.12 slim, /opt/fabflow, app/simulator copies, pip install,
a nonroot fabflow user, and Uvicorn on 0.0.0.0:8000 with one worker. EXPOSE and
containerPort describe ports; they do not publish host ports or start a listener.
Docker host images and kind node runtime images have separate stores; kind load
copies an image into the selected cluster. IfNotPresent uses a local image when
available and attempts a pull otherwise.

Deployment selectors must match template labels. Service selects app=fabflow-api;
EndpointSlice tracks backend addresses, ports, and readiness. Service port 8000
maps through named targetPort http to container port 8000. Service DNS/ClusterIP
remain a stable entry while Pod IPs change. ClusterIP normally has no external IP.

apply submits declarations, not proof of application readiness. rollout status
observes completion. At this point no readiness probe was configured, so Pod Ready
did not prove that Kubernetes had called /health/ready.

## Acceptance and corrections

Build succeeded, initially with tag day instead of day4. An image-not-present
error was addressed by providing docker tag fabflow-api:day fabflow-api:day4;
the deployed day4 image then started. A separate successful kind-load output was
not supplied. A mistyped deployment/k8s/api/yaml path was corrected to
deployments/k8s/api.yaml.

Deployment was 1/1. Pod api-747d5d89c5-6h6jp was Running with zero restarts,
IP 10.244.0.6; Service ClusterIP was 10.96.124.176:8000. EndpointSlice output
was not separately supplied. Forwarding 18000 to 8000 returned
{"status":"ready"}; the screenshot showed Swagger runs/health routes.
Direct openapi.json output was not supplied. These are observations, not fixed IPs.

Service port-forward selects a Pod and uses Kubernetes forwarding; it does not
prove the in-cluster ClusterIP packet path or DNS. Day 5 tested those from the
dashboard. The terminal must remain running; Ctrl+C stops forwarding without
deleting resources. Pod replacement may require restarting the forwarder.
Handling connection is informational; a trailing terminal percent sign is not JSON.

## Troubleshooting and review

Check tags and cluster selection for ImagePullBackOff, logs for CrashLoopBackOff,
and labels/selectors for missing Service backends. Use another host port if occupied.
Prefer a new tag for rebuilds and update/load/apply it explicitly.
The learner explained image copying into kind. The initial idea that Service
records a node location was corrected to Pod label selection with EndpointSlice;
that correction had not yet been independently rechecked in a quiz.

No assistant cluster rerun occurred. The API remained deployed for Day 5, which
added dashboard Deployment, Service, ConfigMap, API URL, and Service-DNS verification.
Reference: [kind image loading](https://kind.sigs.k8s.io/docs/user/quick-start/#loading-an-image-into-your-cluster),
[port-forward](https://kubernetes.io/docs/reference/kubectl/generated/kubectl_port-forward/).

## Recorded commands and examples

These blocks preserve the milestone procedures and recorded output in their original
order. They describe the historical configuration; review current manifests and
prerequisites before repeating them. Resource names and IP addresses are observations,
not fixed values.

```bash
docker context show
kind get clusters
kubectl --context kind-fabflow get nodes
kubectl --context kind-fabflow get namespace fabflow
```

```bash
docker build --target api -t fabflow-api:day4 .
kind load docker-image fabflow-api:day4 --name fabflow
```

```bash
kubectl --context kind-fabflow apply -f deployments/k8s/api.yaml
kubectl --context kind-fabflow -n fabflow rollout status deployment/api --timeout=120s
kubectl --context kind-fabflow -n fabflow get deployments,pods,services -o wide
kubectl --context kind-fabflow -n fabflow get endpointslices -l kubernetes.io/service-name=api
```

```bash
kubectl --context kind-fabflow -n fabflow port-forward service/api 18000:8000
```

```bash
curl --fail-with-body http://127.0.0.1:18000/health/ready
curl --fail-with-body http://127.0.0.1:18000/openapi.json
```

```bash
kubectl --context kind-fabflow -n fabflow describe deployment api
kubectl --context kind-fabflow -n fabflow describe pods -l app=fabflow-api
kubectl --context kind-fabflow -n fabflow logs deployment/api --tail=100
kubectl --context kind-fabflow -n fabflow get events --sort-by=.metadata.creationTimestamp
```

```text
Source code + Dockerfile
        ↓ docker build --target api
fabflow-api:day4 in the Mac Docker image store
        ↓ kind load docker-image --name fabflow
Image in the kind node runtime
        ↓ Deployment → ReplicaSet → Pod
API container runs Uvicorn on port 8000
```

```yaml
# API Pod labels
labels:
  app: fabflow-api

# Service selector
selector:
  app: fabflow-api
```
