# Day 23: CI and Versioned Deployment Handoff

Status: Learner followed the handoff through deployment, manual rollback, and full
result/HTTP acceptance. No independent second operator participated. Actual hours
unrecorded; original documentation awaited commit/CI at this milestone. Progress
23/30 (76.7%). Later closeout: documentation pushed as 9448468 and all four CI jobs
were learner-confirmed passing; remote results were not independently fetched.

## Environment and prerequisite checks

Use repository root, ARM64 kind-fabflow, release fabflow, namespace fabflow-helm.
Raw manifests manage original fabflow; Argo CD later manages fabflow-gitops.
Do not mix managers. Check context, architecture, Git changes, live resources,
current values, and release history before each deployment.

Accepted initial revision: 7, created by Day 21 rollback to 5. API 2/2 at
794dbaafc1697a8812358b30b0808c6100242ebe; dashboard 1/1 at
395df1ec02a010163ea46e68374feb607c0c39bd; postgres:17 1/1. All four Pods initially
zero restarts, PVC Bound; namespace-local Secret postgres-credentials was Opaque.
Only Secret name/type were inspected, not its password.

For a new namespace only, copy .env.example to ignored .env and set a local
POSTGRES_PASSWORD before creating namespace/Secret. Do not blindly replace an
existing Secret: it does not rotate the existing DB role password. Chart creates
init ConfigMap/PVC; SQL initializes empty directories, not migrations. standard/Delete
and no PVC keep policy mean uninstall or deleting PVC/namespace/cluster can destroy
data. Preserve existing namespaces/storage.

## Versioned images and rendering

CI builds images but does not publish a registry, retain downloadable images, or
deploy to kind. The learner confirmed cd361fe's four jobs (quality, containers,
api/dashboard images) passed; no independent remote check was obtained.

Build/load each intended image from its own clean source checkout, using the
matching target and source SHA. Do not label an unrelated checkout as another
commit. Use linux/arm64 for this node. Current values-kind.yaml pins the full
SHA tags above and IfNotPresent; missing local images still trigger remote pulls.
SHA tags identify source, not bit-identical rebuilds with unpinned dependencies.
Update intended tags, then lint, render, inspect replicas/images, and server dry run.
These validation commands do not update the cluster; do not remove dry-run and
use kubectl to manage the Helm resources.

Initial lint passed with optional icon INFO; all nine rendered resources passed
server dry run. Missing last-applied annotation warnings did not indicate mutation.
Initial dashboard-container smoke passed baseline 175/70.5/0 and AMHS 203/142.75/40,
health/HTML, readiness, create/query/metrics/events; not interactive browser acceptance.

## Upgrade, verification, and rollback procedure

Use install for a new release, upgrade for an existing one; always pass values-kind.yaml
to avoid older day13/day5 defaults. Save a full old-result snapshot outside Pods
before updating, then compare summary/metrics/ordered events after updating.
Dashboard smoke creates fresh results and cannot replace old-result verification.
It uses the configured Helm Service directly, avoiding host Compose:8000 confusion.
Readiness ignores DB, so actual create/query checks are required.

For a failed update, inspect history, Pods, Deployment, events, describe, and logs
when a container started. ImagePullBackOff requires tag/runtime-image inspection;
see [Day 21](day21-bad-version-rollback.md). Roll back to the baseline revision
recorded immediately before this deployment. The historical command uses 7, not
a permanent rollback target. Rollback creates a new revision and does not reverse
DB contents or ensure schema compatibility. Rerun values/image/Ready checks, smoke,
and full snapshot verification after recovery.

## Learner execution evidence

1. Both SHA images were already in kind; the API tags shared a crictl image ID.
   No rebuild occurred and equivalent image origin was not inferred from tags.
2. Explicit IPv4 forwarding to 18023 avoided Compose/IPv6 confusion. prepare created
   c9bffe27-def9-466a-ab05-4c87b5b31e05, 201/Location, Mac snapshot
   /tmp/fabflow-day23-before-deploy.json.
3. Same-settings upgrade created revision 8 deployed, terminal timestamp
   November 3, 2026, 21:16:47. Full snapshot/unknown-ID checks passed.
4. rollback to 7 created revision 9 deployed at 21:17:31. These timestamps are
   not command duration or downtime measurements.
5. API 2/2, dashboard/DB 1/1; Pod names/zero restarts unchanged; PVC Bound to
   pvc-5b243a9e-ec4c-4f0a-a87e-2650a639b1dd unchanged.
6. Full result/404 verification passed after rollback. Initially omitted --snapshot
   tried the default Day 12 path; adding it fixed the command, not a DB error.
7. Final dashboard-container smoke passed both workflows and expected KPI values.

Same-version upgrade/rollback did not replace Pods or test distinct application-code
rollout, bad-functional-version recovery, or DB-schema rollback. Day 21's Compose
integrity attribution remains excluded from Helm evidence. Terminal output came
from the learner; no complete raw archive was saved, and Mac /tmp is not a permanent
backup. No update-window failure rate, DB HA, or zero-downtime claim. Only documents
changed; local full Python tests were not rerun in this milestone.

## Recorded commands and examples

These blocks preserve the milestone procedures and recorded output in their original
order. They describe the historical configuration; review current manifests and
prerequisites before repeating them. Resource names and IP addresses are observations,
not fixed values.

```bash
git status --short
kubectl config current-context
kubectl get nodes -o wide
helm history fabflow -n fabflow-helm
helm get values fabflow -n fabflow-helm
kubectl get pods,pvc -n fabflow-helm
kubectl get secret postgres-credentials -n fabflow-helm \
  -o custom-columns=NAME:.metadata.name,TYPE:.type
```

```bash
kubectl create namespace fabflow-helm
kubectl create secret generic postgres-credentials -n fabflow-helm --from-env-file=.env
```

```bash
FABFLOW_SOURCE_SHA=$(git rev-parse HEAD)
docker build --platform linux/arm64 --target api \
  --tag "fabflow-api:$FABFLOW_SOURCE_SHA" .
kind load docker-image "fabflow-api:$FABFLOW_SOURCE_SHA" --name fabflow
```

```bash
helm lint deployments/helm/fabflow -f deployments/helm/fabflow/values-kind.yaml
helm template fabflow deployments/helm/fabflow -n fabflow-helm \
  -f deployments/helm/fabflow/values-kind.yaml
helm template fabflow deployments/helm/fabflow -n fabflow-helm \
  -f deployments/helm/fabflow/values-kind.yaml \
  | kubectl apply --dry-run=server -f -
```

```bash
helm upgrade fabflow deployments/helm/fabflow -n fabflow-helm \
  -f deployments/helm/fabflow/values-kind.yaml --wait --timeout 5m
helm history fabflow -n fabflow-helm
kubectl get deployments -n fabflow-helm \
  -o 'custom-columns=NAME:.metadata.name,READY:.status.readyReplicas,IMAGES:.spec.template.spec.containers[*].image'
kubectl exec -i -n fabflow-helm deployment/fabflow-dashboard -- \
  python - < scripts/smoke_containers.py
```

```bash
helm history fabflow -n fabflow-helm
kubectl get pods -n fabflow-helm
kubectl describe deployment fabflow-api -n fabflow-helm
kubectl get events -n fabflow-helm --sort-by=.metadata.creationTimestamp
```

```bash
helm rollback fabflow 7 -n fabflow-helm --wait --timeout 5m
```
