# Day 25: GitOps Synchronization, Drift, and Reversion

Status: Guided acceptance complete. Final Synced/Healthy, API 2/2, dashboard/DB 1/1,
and HTTP regression passed. Evidence: learner terminal output, without a full raw
archive. Documentation commit/CI pending at milestone; actual hours unrecorded.
Progress 25/30 (83.3%).

## Initial state and tracking main

Reuse Day 24 ARM64 single-node kind-fabflow, Argo CD v3.6.0, Application
fabflow-gitops in argocd, destination fabflow-gitops, external Secret/PVC retained.
Raw fabflow and Helm fabflow-helm remain separate. Original target 9448468,
values-kind.yaml, manual sync. Changing targetRevision to main and refreshing
resolved 63a5de770ce2e7139afb4bec7ad40e94b708a226 while Synced/Healthy: a docs-only
commit need not change rendered resources. Tracking main updates comparison state;
manual sync is still needed. Auto-sync/self-heal stayed disabled.

## Git tag change and manual sync

The node contained both full API SHA tags, sharing image ID 3c86c5d31210f.
This was a tag/deployment configuration exercise, not distinct application-code
versions. Only API values-kind.yaml tag changed 794dbaa -> 395df1e; dashboard stayed.
Lint passed (icon INFO), diff checks passed, then commit
b05f4236e21d803ec8c0a2cc05a96c7668c3ab27 was pushed. Refresh showed that revision
OutOfSync/Healthy while the live API still used 794dbaa, proving unapplied Git change.

UI Sync failed with Request has been terminated and forwarding repeatedly refused
8080. Application operation was empty, last successful revision remained 9448468,
and image unchanged, so no new server-side operation was observed before retry.
A manual operation submitted through Kubernetes API synced explicit b05f423.
initiatedBy.username is audit metadata, not authentication or authorization change;
execution uses the caller's Kubernetes permission and Argo CD controller, independent
of UI forwarding. Operation Succeeded, API tag became full 395df1e, rollout completed,
and HTTP smoke passed after Synced/Progressing settled.

## Live drift and correction

Scaling the live API Deployment to one left Git replicas=2. Observed live 1/1,
Application OutOfSync/Healthy: healthy workloads can still differ from desired state.
Manually syncing b05f423 restored 2/2, Succeeded, Synced/Healthy. This is manual
drift correction, not automatic self-healing acceptance.

## Git revert and final regression

With clean tree and verified single-file scope, git revert --no-edit b05f423
created 12477cc672179bc12dd9abf3d842f18f42b1bbd3, restoring desired API tag
794dbaafc1697a8812358b30b0808c6100242ebe. The learner pushed; assistant local
inspection confirmed main/origin/main there. Remote CI was not independently checked.
Refresh showed OutOfSync/Healthy; explicit manual sync to 12477cc succeeded,
rollout completed, and later output showed Synced/Healthy with API 2/2 and
Dashboard/DB 1/1. Final dashboard-container smoke passed baseline 175/70.5/0,
AMHS 203/142.75/40, health/HTML, readiness, and all HTTP workflows.

Reverting Git then syncing aligns desired/live state. Changing only live state
would be overwritten by the next sync. Helm rollback was not used for this environment.

## Argo CD incident evidence and limits

Server repeatedly refused 8080. Previous container Completed/exit 0 coincided with
liveness-failure Killing events, so exit 0 did not rule out probe-triggered termination.
Server restarts reached 2, notifications 2; repo-server briefly 0/1 with zero restarts.
repo-server HTTP probes timed out while later GenerateManifest/gRPC health calls
returned OK; that does not prove every HTTP probe was healthy. All seven components
later Ready. Node Ready alone did not establish cause of intermittent refusal/timeouts.
No probe changes, Pod deletion, or Docker restart was used for recovery.

No continuous availability/performance measurement, zero-downtime evidence, old-result
snapshot acceptance, independent checks of the other namespaces during incidents,
PVC changes, prune, schema rollback, auto-sync, or self-heal tests. Only records were
updated; no full Pytest rerun. Day 26 later summarized measurements and architecture.

## Recorded commands and examples

These blocks preserve the milestone procedures and recorded output in their original
order. They describe the historical configuration; review current manifests and
prerequisites before repeating them. Resource names and IP addresses are observations,
not fixed values.

```bash
kubectl patch application fabflow-gitops -n argocd --type merge \
  -p '{"spec":{"source":{"targetRevision":"main"}}}'
kubectl annotate application fabflow-gitops -n argocd \
  argocd.argoproj.io/refresh=hard --overwrite
```

```bash
kubectl patch application fabflow-gitops -n argocd --type merge \
  -p '{"operation":{"initiatedBy":{"username":"kubectl-manual"},"sync":{"revision":"b05f4236e21d803ec8c0a2cc05a96c7668c3ab27","prune":false}}}'
```

```bash
kubectl scale deployment fabflow-gitops-api -n fabflow-gitops --replicas=1
```

```bash
git revert --no-edit b05f423
git show --oneline HEAD -- deployments/helm/fabflow/values-kind.yaml
git push origin main
```

```bash
kubectl patch application fabflow-gitops -n argocd --type merge \
  -p '{"operation":{"initiatedBy":{"username":"kubectl-manual"},"sync":{"revision":"12477cc672179bc12dd9abf3d842f18f42b1bbd3","prune":false}}}'
kubectl rollout status deployment/fabflow-gitops-api -n fabflow-gitops --timeout=60s
```

```bash
kubectl exec -i -n fabflow-gitops deployment/fabflow-gitops-dashboard -- \
  python - < scripts/smoke_containers.py
```
