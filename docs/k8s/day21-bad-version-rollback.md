# Day 21: Bad Image and Manual Rollback

Status: Failure diagnosis and manual rollback accepted. The original localhost data
check was later identified as Compose in Day 22 and is excluded from Helm integrity
evidence. Actual hours unrecorded; commit/CI were pending at the milestone.

## Baseline

Learner output and artifacts/day21 show single-node kind-fabflow Ready,
fabflow-helm revision 5 deployed, API 2/2 and dashboard/DB 1/1, zero restarts.
API SHA 794dbaafc1697a8812358b30b0808c6100242ebe; dashboard SHA
395df1ec02a010163ea46e68374feb607c0c39bd; RollingUpdate 1/0. PVC Bound to
pvc-5b243a9e-ec4c-4f0a-a87e-2650a639b1dd.

prepare originally intended to use Helm forwarding but actually reached Compose
IPv4 localhost:8000, creating 5edf7556-d9e5-404b-adb1-3bc512cac086 with 201/Location.
The full snapshot artifacts/day21/before-run.json remains unchanged.

## Failure and diagnosis

Upgrade to day21-intentionally-missing, without automatic rollback, started
November 3, 2026 at 03:27:08Z and ended 03:28:38Z, exit 1, 90-second wait.
Revision 6 failed with context deadline exceeded and Updated 1/2. This is command
waiting duration, not downtime. Pod fabflow-api-67756b6786-86fb6 never started:
ErrImagePull then ImagePullBackOff, pull access denied/insufficient_scope for
Docker Hub library/fabflow-api. Missing local tag plus IfNotPresent caused a pull.
Events alone cannot distinguish nonexistent repository from insufficient permission;
registry login was not required to complete this intentional failure exercise.

READY/AVAILABLE 2 referred to old h8qbh/zxp8q; UP-TO-DATE 1 meant the new template,
not readiness. maxSurge=1 allowed the extra Pod; maxUnavailable=0 retained old
available replicas but did not prove every request succeeded.

## Rollback

Rollback to revision 5 created revision 7 deployed; revision 6 stayed failed and
5 superseded. Command bounds: 03:32:58Z–03:32:59Z, exit 0, shell SECONDS=0.
Coarse second-resolution timing cannot establish zero-second recovery or outage
recovery duration. API tag/desired/updated/available returned to two; original
old Pods, dashboard/DB, and PVC/PV were unchanged with zero API restarts.

The original full snapshot/unknown-ID verification passed against Compose, not Helm.
No continuous HTTP sampling occurred. Functional bad versions, schema rollback,
DB HA, and whole-cluster recovery were not tested. The learner acknowledged the
conceptual explanation without a separate quiz answer; no application/chart changes
or full Pytest rerun occurred. Progress then recorded 21/30 (70%).

## Day 22 correction: IPv4 and IPv6 reached different environments

Docker owned 127.0.0.1:8000 while Helm forwarding listened only on [::1]:8000.
Day 21 explicitly used IPv4. Day 22 Helm Service and both direct API Pods returned
404 for that run; API selected postgres at fabflow-postgres/10.244.0.17 with zero
matching DB rows. localhost:8000 still matched the original snapshot. This is an
environment attribution error, not evidence of Helm data loss.

Original artifacts were preserved; the assistant's prior interpretation was premature.
Failure/rollback workload evidence remains valid, but Helm rollback integrity was
not verified here. Day 22 created a new snapshot through the fixed dashboard and
Helm Service; that does not retroactively establish Day 21 rollback integrity.
See [Day 22](day22-pod-recovery.md), [rollback log](../../artifacts/day21/rollback.log),
[failed events](../../artifacts/day21/failed-pod-events.txt), and
[history](../../artifacts/day21/after-helm-history.txt).

## Recorded commands and examples

These blocks preserve the milestone procedures and recorded output in their original
order. They describe the historical configuration; review current manifests and
prerequisites before repeating them. Resource names and IP addresses are observations,
not fixed values.

```bash
helm upgrade fabflow deployments/helm/fabflow --namespace fabflow-helm \
  -f deployments/helm/fabflow/values-kind.yaml \
  --set-string api.image.tag=day21-intentionally-missing --wait --timeout 90s
```

```bash
helm rollback fabflow 5 --namespace fabflow-helm --wait --timeout 90s
```
