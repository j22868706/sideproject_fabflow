# Day 27: README, Troubleshooting, and Demonstration

Status: Guided operational checks complete; README/runbook entry points and a
five-minute presentation outline are written. Timed rehearsal/recording is pending,
so the full lesson remains in progress. Actual hours unrecorded; progress remains
26/30 complete. Documentation awaits commit/CI; Day 28 has not started.

## Operational evidence

Evidence is learner-provided terminal output in the teaching session, without a
separate complete raw archive. The Mac snapshot
/tmp/fabflow-day27-before-demo.json is outside Git and is not a permanent backup.

| Step | Verified result |
| --- | --- |
| Initial state | kind-fabflow, fabflow-helm release fabflow revision 9 deployed; API 2/2, dashboard/DB 1/1, 1Gi standard PVC Bound |
| Explicit connection | IPv4 127.0.0.1:18027 Service forwarding; readiness 200 |
| Create | Run 3e22d17d-773a-4d3f-a769-defdece02707; 201/Location; full summary/metrics/142-event snapshot |
| Original replicas | Direct HTTP on 9dltm/xbk64 matched all three full responses |
| Normal deletion | 9dltm replaced by jhbl7; new Pod Ready and all three responses matched |
| Tag switch | Revision 10 deployed, API 794dbaa -> 395df1e; new hpzvc/mnmjg each matched full results |
| Rollback | Target revision 9 settings; new revision 11 deployed, API restored to 794dbaa |
| Final acceptance | jbzd6/pl8lc each matched summary/metrics/events and returned 404 on all three unknown-ID endpoints |

Full API baseline tag: 794dbaafc1697a8812358b30b0808c6100242ebe; alternate and
dashboard tag: 395df1ec02a010163ea46e68374feb607c0c39bd. crictl showed both API
tags loaded with the same ID:
sha256:3c86c5d31210f742b02a7d6a6a507214907a556f3bf374b6c61a135fdb19dfe8.
This demonstrates tag/deployment changes, not distinct application functionality.
Dashboard/DB kept their Pod names; final API restarts zero, dashboard 3, DB 0.
PVC/PV were not independently queried again at the end.

No continuous HTTP sampling or full recovery timer was used. The new Pod's age
of about 21s when Ready is not a measured recovery or outage duration. No zero-downtime
claim. The failed final 404-print command was corrected and all checks rerun as
needed; details are in troubleshooting below.

## Audience and prerequisites

Commands target Bash/Zsh, local ARM64 kind-fabflow, namespace fabflow-helm, release
fabflow. Use the actual repository root and an environment with the project installed.
The recorded Mac checkout is /Volumes/externalssd/swe/fabflow; adjust for another
machine. Confirm context, live release/history/values, Ready API replicas, and Bound
PVC before starting. [Day 23](day23-deployment-handoff.md) covers image build/load,
external Secret, and first installation; this demonstration assumes installation.
Manage fabflow-gitops with Argo CD separately, not these Helm commands.

Inspect node images and record the current deployed baseline revision before any
change. Revision 9 was this session's target, not a permanent target; the session
ended at 11. The two SHA tags must already be loaded. Keep explicit IPv4 forwarding
on port 18027 running in a separate terminal to avoid Compose port 8000 confusion.

## Five-minute presentation outline (not yet timed)

| Target time | Screen/action | Talking point |
| --- | --- | --- |
| 0:00–0:40 | [Architecture](day26-measurements-architecture.md) and Pod status | Synchronous simulation, commit completed results, shared DB, single-node/single-DB limits |
| 0:40–1:20 | Readiness, prepare, external snapshot | 201 follows commit; show run_id |
| 1:20–2:00 | Direct checks on both named Pods | Identical complete summary, metrics, and ordered events |
| 2:00–3:00 | Delete one API Pod; verify replacement | Controller restores replicas; saved results outlive API process |
| 3:00–4:30 | Tag switch, verify, rollback, verify | Inspect image availability/target; rollback creates a new revision; tags share content |
| 4:30–5:00 | Conclusions and boundaries | Ready does not imply DB health; PVC is not backup; no downtime measurement |

Local startup/rollout duration varies. If the live workflow exceeds five minutes,
extend and report actual time or explicitly distinguish previously recorded evidence
from live operations. Do not present edited/precompleted waits as measured duration.
The following recorded blocks provide environment checks, snapshot creation, direct
Pod verification, normal deletion, tag switching, rollback, and diagnostic commands.
Read each phase's requirements before execution.

## Running the phases

1. Change to the actual repository root. Verify script/Chart.yaml existence, context,
   values/history, Pods/PVC, and loaded images before live changes.
2. Start explicit IPv4 Service forwarding. Create using prepare with a new snapshot
   filename. Existing snapshots are retained for verify; prepare refuses overwrite.
3. List current API Pods using instance/component labels and replace
   ACTUAL_API_POD_NAME with each actual Ready, nonterminating Pod. The inline Python
   reads the snapshot from stdin and directly queries Pod-local API. Check exit 0
   and six PASS lines per Pod. It does not import the snapshot into the database.
4. Normally delete one selected Pod, without force. Watch until the old Pod is gone
   and two APIs are Ready, then stop watch and verify the new named Pod. Restart
   forwarding if it lost its selected Pod.
5. Check the starting tag differs from the alternate, or there may be no rollout.
   Upgrade using values-kind.yaml plus the alternate API tag, then inspect images/
   Pods and verify both new Pods. The command-line override does not edit Git.
6. Replace BASE_REVISION with the number recorded immediately before the exercise,
   rollback, inspect the new revision/image/Pods, and verify both final replicas.
   Never use this session's historical 9 without checking the current baseline.

The shell wraps Python in single quotes; Python strings inside use double quotes.
Do not place an unescaped Python single-quoted literal inside that shell string.
For a new snapshot filename, change every matching command consistently.

## Troubleshooting

| Symptom | Diagnosis and response |
| --- | --- |
| Python cannot find scripts/check_postgres_persistence.py | Absolute path succeeded; pwd was not captured, so the directory mismatch cause is unconfirmed. Check pwd/file existence and enter actual repository root |
| Helm: repo deployments not found | Relative chart path was unresolved and interpreted as repo/chart; absolute path succeeded. Use ./deployments/helm/fabflow with Chart.yaml present. The failed attempt did not update the release |
| Readiness 200 but result request 503 | Readiness does not query DB; inspect API/DB state, logs, Service, and real create/query behavior |
| Forwarder disconnect/refusal | Inspect forwarding terminal, Pods, and port occupancy; restart explicit IPv4 18027 after selected Pod replacement |
| NameError: summary while printing 404 result | Assistant's original Python single quotes conflicted with shell quoting. Use label = suffix or "summary". Full comparisons had passed; corrected unknown-ID checks then passed separately on both Pods |
| ContainerCreating or Running with 0/1 | Inspect describe/events/logs/probes before deleting/restarting anything; Running is not Ready |
| ImagePullBackOff | Check full tag, node runtime image, pull policy, and events; see [Day 21](day21-bad-version-rollback.md) |

Use actual Pod names in describe/logs, and inspect ordered namespace events and API
EndpointSlices. Preserve DB/PVC and all namespaces; uninstall/storage deletion is
not required. [Day 26](day26-measurements-architecture.md) documents measurement and
failure boundaries.

## Remaining acceptance

Time one presentation rehearsal and record total duration, overrun, and confusing
steps; recording is optional. Then adjust the outline and synchronize Day 27 status.
The lesson remains in progress while the learner requests whole-project English
review. File/command examples were checked for local links, Python syntax, and shell
quoting; documentation work alone did not trigger another full application test run.

## Recorded commands and examples

These blocks preserve the milestone procedures and recorded output in their original
order. They describe the historical configuration; review current manifests and
prerequisites before repeating them. Resource names and IP addresses are observations,
not fixed values.

```bash
cd /Volumes/externalssd/swe/fabflow
pwd
test -f scripts/check_postgres_persistence.py
test -f deployments/helm/fabflow/Chart.yaml
kubectl config current-context
helm list -n fabflow-helm
helm history fabflow -n fabflow-helm
helm get values fabflow -n fabflow-helm
kubectl get deployments,pods,pvc -n fabflow-helm
```

```bash
docker exec fabflow-control-plane crictl images --no-trunc
```

```bash
kubectl port-forward -n fabflow-helm --address 127.0.0.1 service/fabflow-api 18027:8000
```

```bash
curl --fail-with-body -i http://127.0.0.1:18027/health/ready
python scripts/check_postgres_persistence.py prepare \
  --api-url http://127.0.0.1:18027 \
  --snapshot /tmp/fabflow-day27-before-demo.json
```

```bash
kubectl get pods -n fabflow-helm \
  -l app.kubernetes.io/instance=fabflow,app.kubernetes.io/component=api

kubectl exec -i -n fabflow-helm ACTUAL_API_POD_NAME -- python -c '
import json
import sys
from uuid import uuid4
from urllib.error import HTTPError
from urllib.request import urlopen

snapshot = json.load(sys.stdin)
base = "http://127.0.0.1:8000/api/v1/runs/"
for key, suffix in [("summary", ""), ("metrics", "/metrics"), ("events", "/events")]:
    with urlopen(base + snapshot["run_id"] + suffix, timeout=10) as response:
        actual = json.load(response)
    assert actual == snapshot[key], f"{key} differs"
    print(f"PASS: {key} matches snapshot")

unknown = str(uuid4())
for suffix in ["", "/metrics", "/events"]:
    try:
        with urlopen(base + unknown + suffix, timeout=10):
            raise AssertionError("Expected 404")
    except HTTPError as error:
        assert error.code == 404, error.code
    label = suffix or "summary"
    print(f"PASS: unknown ID {label} returns 404")
' < /tmp/fabflow-day27-before-demo.json
```

```bash
kubectl delete pod ACTUAL_API_POD_NAME -n fabflow-helm --wait=false
kubectl get pods -n fabflow-helm -w
```

```bash
helm upgrade fabflow ./deployments/helm/fabflow \
  --namespace fabflow-helm \
  -f deployments/helm/fabflow/values-kind.yaml \
  --set-string api.image.tag=395df1ec02a010163ea46e68374feb607c0c39bd \
  --wait --timeout 2m
kubectl get deployment fabflow-api -n fabflow-helm \
  -o jsonpath='{.spec.template.spec.containers[0].image}{"\n"}'
kubectl get pods -n fabflow-helm
```

```bash
helm rollback fabflow BASE_REVISION --namespace fabflow-helm --wait --timeout 2m
helm history fabflow -n fabflow-helm
kubectl get deployment fabflow-api -n fabflow-helm \
  -o jsonpath='{.spec.template.spec.containers[0].image}{"\n"}'
kubectl get pods -n fabflow-helm
```

```bash
kubectl describe pod ACTUAL_API_POD_NAME -n fabflow-helm
kubectl logs ACTUAL_API_POD_NAME -n fabflow-helm --tail=100
kubectl get events -n fabflow-helm --sort-by=.metadata.creationTimestamp
kubectl get endpointslices -n fabflow-helm -l kubernetes.io/service-name=fabflow-api
```
