# Day 3: Local Kubernetes Environment

Status: Core acceptance complete from learner-provided terminal output. Estimate:
2 hours; actual hours unrecorded. The [extended English walkthrough](day03-local-cluster-en.md)
explains the commands in more detail. API deployment was deferred to Day 4.

## Setup and concepts

The assistant found kind v0.33.0 and kubectl client v1.36.1. The existing
`yunikorn-dev` cluster was preserved; a separate kind cluster named `fabflow`
was created. Docker must be running before cluster creation. The resulting
context was kind-fabflow and node fabflow-control-plane was Ready.

kind runs Kubernetes nodes as containers. kubectl communicates with the Kubernetes
API. A kubeconfig context combines cluster, identity, and default namespace; it is
separate from Docker context. Namespaces scope resources within a cluster without
automatically providing network isolation. This single node runs control-plane
components and workloads, so it is not a highly available production topology.
Commands explicitly select the context to avoid modifying the other cluster.

## Observed acceptance

| Item | Evidence |
| --- | --- |
| Cluster/node | kind-fabflow reachable; node reports Kubernetes v1.37.0; no separate API-server version output supplied |
| Node environment | 172.18.0.3, control-plane, Debian GNU/Linux 13, containerd://2.3.4 |
| Namespace | fabflow created; test Pod creation, inspection, and deletion succeeded |
| Test Pod | day3-smoke, 1/1 Running, zero restarts; Pod IP 10.244.0.5 on fabflow-control-plane |
| Container execution | exec returned hello-fabflow |
| Deletion | No resources found in fabflow namespace; standalone Pod was not recreated |

Node IP and Pod IP belong to different network layers. exec runs an additional
command inside an existing container; `--` separates kubectl arguments from the
container command. This Pod had no Deployment controller, so deletion did not
trigger replacement. restart=Never is a container restart policy, a separate
mechanism from a Deployment creating a new Pod.

## Rebuild reference and limits

Cluster deletion/recreation commands were documented but not executed. The cluster
and images were retained for Day 4. Deleting a cluster removes its resources and
can destroy local data; do not repeat this historical exercise against the later
PostgreSQL/PVC deployment without a backup and recovery plan. Never delete the
unrelated yunikorn-dev cluster for this exercise.

Evidence came from the learner's teaching session, not assistant reruns or a
separate screenshot archive. No errors were reported in this segment.
References: [kind quick start](https://kind.sigs.k8s.io/docs/user/quick-start/),
[kubeconfig contexts](https://kubernetes.io/docs/concepts/configuration/organize-cluster-access-kubeconfig/).

## Recorded commands and examples

These blocks preserve the milestone procedures and recorded output in their original
order. They describe the historical configuration; review current manifests and
prerequisites before repeating them. Resource names and IP addresses are observations,
not fixed values.

```bash
kind version
kubectl version --client
kind get clusters
kind create cluster --name fabflow --wait 120s
kubectl config current-context
kubectl --context kind-fabflow cluster-info
kubectl --context kind-fabflow get nodes -o wide
```

```bash
kubectl --context kind-fabflow create namespace fabflow
kubectl --context kind-fabflow -n fabflow run day3-smoke --image=busybox:1.37.0 --restart=Never --command -- sleep 3600
kubectl --context kind-fabflow -n fabflow wait --for=condition=Ready pod/day3-smoke --timeout=120s
kubectl --context kind-fabflow -n fabflow get pods -o wide
kubectl --context kind-fabflow -n fabflow exec day3-smoke -- echo hello-fabflow
kubectl --context kind-fabflow -n fabflow delete pod day3-smoke
kubectl --context kind-fabflow -n fabflow get pods
```

```bash
kind delete cluster --name fabflow
kind create cluster --name fabflow --wait 120s
kubectl --context kind-fabflow create namespace fabflow
```

```text
hello-fabflow
pod "day3-smoke" deleted from fabflow namespace
No resources found in fabflow namespace.
```
