# Day 24: Local Argo CD Demonstration

Status: Guided installation, UI login, manual sync, image checks, and HTTP acceptance
complete. Evidence: learner terminal output/UI reports, without a full raw archive.
Actual hours unrecorded; progress 24/30 (80%). Documentation later pushed as 63a5de7;
its CI status was not confirmed at closeout.

## Environment and installation

ARM64 single-node kind-fabflow; initially node Ready and fabflow-helm revision 9
deployed. Preserve raw fabflow and Helm fabflow-helm; Argo CD manages a separate
fabflow-gitops. All share one node, so namespace separation is not node isolation.
The learner confirmed Day 23 commit 9448468's four CI jobs passed; not independently
fetched. Follow the [official getting-started procedure](https://argo-cd.readthedocs.io/en/stable/getting_started/).
Create/install commands apply only to a new environment.

All seven Argo CD Pods initially Ready/zero restarts. Floating stable manifests
were used without an archived digest; repeating them may install a different
version. Server logs identified v3.6.0, commit f55566445ee3a2a4f3339bf10df0f6bc1ecf7f23.
Forwarding service/argocd-server 18080:443 printed 18080->8080 due to targetPort.
The learner logged into https://127.0.0.1:18080 as admin; retrieve initial password
only in a private terminal, never paste/commit it. Check local address before
handling the default-certificate warning. Restart forwarding after Server Pod
recovery if disconnected; Ctrl+C stops forwarding, not Argo CD.

## Application configuration

Create destination namespace and its external Secret from ignored .env only if
absent. Secrets cannot cross namespaces. The new environment has its own DB/PVC.

| Setting | Accepted value |
| --- | --- |
| Name/project | fabflow-gitops / default |
| Repository | https://github.com/j22868706/sideproject_fabflow.git |
| Target revision | 9448468, pinned commit at this milestone |
| Path | deployments/helm/fabflow |
| Helm valueFiles | values-kind.yaml |
| releaseName | Unset; defaults to Application name fabflow-gitops |
| Destination | https://kubernetes.default.svc, namespace fabflow-gitops |
| Sync | Manual, no auto-sync, Prune, or Force |

Initial UI setup omitted Helm settings and deployed day13/day5. An assistant
check against fabflow-dashboard failed NotFound because actual names were
fabflow-gitops-*. spec.source.helm was empty; patching valueFiles corrected it
without changing releaseName/resource prefixes. UI Refresh/Sync/Synchronize still
had to apply changes. Synced/Healthy alone does not prove correct image values;
inspect images and HTTP. Argo CD renders Helm resources here; do not use Helm
upgrade/rollback to manage this environment.

## Intermittent failures and recovery

Forwarding failed with Pod-local localhost:8080 connection refused. Server became
0/1 and restarted once, then listened again and recovered. Previous logs/termination
reason were not captured; a warning log is not established restart cause.
After sync there were probe timeouts, NodeNotReady, etcd request timeouts, and
Endpoint/EndpointSlice update failures. API briefly showed 3/2 during surge;
DB Deployment/Pod observations also differed temporarily. Node later Ready with
Memory/Disk/PID Pressure False.

Observed node: about 3.825GiB, 8 CPU, 29 Pods; memory requests 59%, limits 178%;
Argo CD lacked resource requests/limits. Requests are not usage and overcommitted
limits do not prove OOM. One docker stats sample: CPU 821.53%, memory 1.827/3.825GiB
(47.76%). BLOCK I/O 108GB/12.4GB is cumulative, not current rate. ps lifetime-average
CPU is not directly comparable to a short stats sample; no single process was
identified as cause. CPU contention is possible, not confirmed.
No Pod deletion, Docker restart, or probe editing was used for recovery.

## Final acceptance and boundaries

Application reached Synced/Healthy; API 2/2, dashboard/DB 1/1. API b44xc had one
restart, sz8mt zero; dashboard/DB zero. Accepted images: API full SHA 794dbaa,
dashboard 395df1e (full tags in Day 23), postgres:17. UI source revision 9448468
is the chart/values source, distinct from application-image source SHAs.
Final smoke passed baseline 175/70.5/0 and AMHS 203/142.75/40, dashboard health/HTML,
readiness, and both create/query/metrics/events workflows.

This final snapshot does not prove long-term stability or uninterrupted service.
No auto-sync, Git-change deployment, full old-result comparison across updates,
Application deletion, or registry publication was tested. Retain all namespaces/PVCs;
chart has no keep policy. Only docs/workbook changed; no app/chart or full Pytest rerun.
Day 25 later tested Git desired-state changes and manual synchronization.

## Recorded commands and examples

These blocks preserve the milestone procedures and recorded output in their original
order. They describe the historical configuration; review current manifests and
prerequisites before repeating them. Resource names and IP addresses are observations,
not fixed values.

```bash
kubectl config current-context
kubectl create namespace argocd
kubectl apply -n argocd --server-side --force-conflicts \
  -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml
kubectl get pods -n argocd
```

```bash
kubectl port-forward -n argocd \
  --address 127.0.0.1 service/argocd-server 18080:443
```

```bash
kubectl get secret argocd-initial-admin-secret -n argocd \
  -o jsonpath='{.data.password}' | base64 -d
```

```bash
kubectl create namespace fabflow-gitops
kubectl create secret generic postgres-credentials \
  -n fabflow-gitops --from-env-file=.env
```

```bash
kubectl patch application fabflow-gitops -n argocd --type merge \
  -p '{"spec":{"source":{"helm":{"valueFiles":["values-kind.yaml"]}}}}'
kubectl get application fabflow-gitops -n argocd \
  -o jsonpath='{.spec.source.helm}{"\n"}'
```

```bash
kubectl get application fabflow-gitops -n argocd \
  -o jsonpath='{.status.sync.status}{" / "}{.status.health.status}{"\n"}'
kubectl get deployments -n fabflow-gitops \
  -o 'custom-columns=NAME:.metadata.name,IMAGES:.spec.template.spec.containers[*].image'
kubectl exec -i -n fabflow-gitops deployment/fabflow-gitops-dashboard -- \
  python - < scripts/smoke_containers.py
```
