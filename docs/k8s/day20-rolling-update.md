# Day 20: Rolling Update Measurement

Status: API image-tag update, continuous HTTP sampling, and data acceptance complete.
Five failed requests were observed; zero downtime is not claimed. PR/main closeout
was learner-confirmed. Progress 20/30 (66.7%); actual hours unrecorded.

## Environment and change

ARM64 single-node kind-fabflow, namespace fabflow-helm, two APIs and one DB.
Initial release revision 4 and clean working tree. Branch feat/day20-rolling-update,
commit 794dbaafc1697a8812358b30b0808c6100242ebe, adds explicit API RollingUpdate
maxSurge=1/maxUnavailable=0 and scripts/probe_rolling_update.py; prior defaults were
25%/25%. Readiness still ignores DB, minReadySeconds=0. No API application-code
change occurred; an image-tag change triggered the deployment exercise.

API was built locally linux/arm64 from the clean commit and loaded into kind;
build image ID sha256:63322f0667620930a6f33279aa95d9124eae776795f19e29cda92cfbdf884b98.
Only API tag changed; dashboard retained 395df1ec02a010163ea46e68374feb607c0c39bd
so the measurement client would not be replaced.

## Method and results

Fixed dashboard Pod called http://fabflow-api:8000 sequentially: readiness, saved
summary, metrics, events. Target cycle interval 0.5s, per-request timeout setting 2s,
no retries; slow calls delay later cycles. Compare complete results to a snapshot.
JSONL records start UTC, monotonic elapsed, status, latency, error. This was not a
load test and did not identify each request's destination Pod.
Run 35e5a9c1-87e2-4eb6-a08b-9428c61a2d47 had 142 events; snapshot copied from
Pod /tmp to Mac before update. Five-second trial: ten calls/endpoint, no failures.

Formal observation: November 1, 2026, request starts 22:50:47.480291Z through
22:55:47.454167Z, approximately 300 seconds. Helm upgrade --wait --timeout 2m ran
22:53:06Z–22:53:12Z (second-resolution bounds), measured 6.818s, exit 0,
revision 5 deployed. This is command duration, not downtime.

| Endpoint | Requests | Failures |
| --- | ---: | ---: |
| Readiness | 594 | 0 |
| Summary | 594 | 2 |
| Metrics | 594 | 0 |
| Events | 594 | 3 |
| Total | 2,376 | 5 |

Full-window failure proportion: 0.2104%, not update-only failure rate or long-term
availability. Three connection refusals/two timeouts had no HTTP status. Failed
starts spanned 22:53:10.219356Z–22:53:13.703797Z; timeouts took about 2004ms and
completed later. This span does not establish continuous total outage.

## Rollout and data evidence

Events showed new RS 0->1, old 2->1, new 1->2, old 1->0. New API Pods
7bfd9c659d-h8qbh/zxp8q were Ready/zero restarts at the target SHA. Dashboard
899996b87-fvxgt and DB 7b879c7d67-tsf4s were unchanged. Deployment revision 3 and
Helm revision 5 are different counters. Post-update full snapshot verification and
three unknown-ID 404s passed. No new two-preset smoke/browser rerun occurred here.

Failures were near old-Pod replacement, but termination/routing timing remains a
hypothesis: no destination-Pod mapping, old-container termination logs, or EndpointSlice
timeline was captured. DB/API readiness events about 24 minutes earlier cannot
establish this update's cause. maxUnavailable=0 does not guarantee every HTTP request.
No preStop/grace-period/shutdown changes, improvement retest, or rollback occurred.

## Evidence and closeout

[Raw JSONL](../../artifacts/day20/fabflow-day20-rolling-update.jsonl),
[upgrade log](../../artifacts/day20/fabflow-day20-upgrade.log),
[snapshot](../../artifacts/day20/fabflow-day20-before-update.json),
[deployment](../../artifacts/day20/api-deployment-after.yaml), and
[events](../../artifacts/day20/events-after.json) are preserved. A .gitignore exception
retains logs; the upgrade log includes session-close output, with EXIT_CODE=0 and
Helm result establishing success. Assistant independently checked raw counts,
errors/times, probe Ruff/format, and mocked matching/mismatch branches. Learner
Helm lint passed (icon INFO).

Measurement commit 794dbaa; evidence commit a084f55;
[PR 3](https://github.com/j22868706/sideproject_fabflow/pull/3) was learner-confirmed
passing/conflict-free and merged. Terminal showed main/origin/main c750798;
learner confirmed all four main CI jobs passed. Remote checks were not fetched
independently. Merge did not deploy locally; last accepted release was revision 5.
Day 20 closeout is complete. Day 21 later exercised a bad tag and manual rollback.
