# Day 22: API Pod Replacement Measurement

Status: Three normal single-Pod deletions and final data acceptance complete.
Actual hours unrecorded; commit/CI were pending at the milestone. Raw data is
preserved in artifacts/day22 and was independently checked by the assistant.

## Environment and corrected baseline

Single-node ARM64 kind-fabflow (node v1.37.0), fabflow-helm revision 7 deployed,
API 2/2, dashboard/DB 1/1, initially zero restarts. API SHA 794dbaa and dashboard
395df1e match the full tags in Day 20. Single DB and original Day 21 PVC/PV.
Initial trial using Day 21's snapshot: readiness 10/10 succeeded but all three
result endpoints returned ten 404s each. Correct EndpointSlice backends were
10.244.0.22/23; direct Pod queries also returned not found, and DB 10.244.0.17 had
zero matching rows. localhost:8000 still matched. Learner lsof/ps/docker output
identified Compose IPv4 versus Helm IPv6 forwarding, correcting Day 21 attribution.
No data loss was established. Diagnostic session output was not separately archived;
the failed [trial JSONL](../../artifacts/day22/trial.jsonl) remains intact.

After stopping unnecessary forwarding, fixed dashboard Pod
fabflow-dashboard-899996b87-fvxgt created f0c1b40d-ccda-476c-982e-14360e17803a
through http://fabflow-api:8000. 201/Location passed; snapshot copied from
/tmp/day22-helm-before-run.json to Mac before-run.json. Correct five-second trial:
ten calls per endpoint, no failures ([trial](../../artifacts/day22/trial-helm.jsonl)).

## Method and timing definition

Each formal observation lasted 120s using probe_rolling_update.py from that fixed
Pod, target cycle every 0.5s, sequential readiness/summary/metrics/events, no retry,
complete result comparison. timeout=2 is a socket/urllib setting, not a strict
whole-request deadline; slow calls/scheduling delay later cycles, so counts differ.
This was not a load test or strict uniform sampling.

Mac monotonic timing began before normal kubectl delete --wait=false, without force.
Polling waited 0.5s after each query and ended when the old Pod name was absent
and two nonterminating API Pods were Ready. Duration includes command/API-server/
polling overhead, not pure startup or HTTP downtime. First-new-Pod Ready and
Deployment availableReplicas=2 were not separately timestamped.

## Results (UTC, November 3, 2026)

| Attempt | Deleted suffix | Delete start | Recovery confirmed | Observed seconds | Requests | Failures |
| --- | --- | --- | --- | ---: | ---: | ---: |
| 1 | h8qbh | 03:47:58.562784 | 03:48:01.611242 | 3.049 | 960 | 2 |
| 2 | zxp8q | 03:49:58.051739 | 03:50:01.746065 | 3.694 | 908 | 1 |
| 3 | lb4bv | 03:52:50.448771 | 03:52:54.031848 | 3.583 | 960 | 0 |

All deletions/recoveries occurred within their sampling windows. Total 2,828 requests,
three failures (0.1061%) across full windows, not fault-only failure rate or long-term
availability. Attempt 1 had 240 calls/endpoint; metrics/events connection refusals
started 03:47:58.716155Z/.721748Z, about 0.15s after deletion. Time proximity does
not identify root cause; no destination-Pod/EndpointSlice timeline was captured.
Attempt 2 had 227 calls/endpoint; metrics timeout at 03:51:18.798661Z took
4146.716ms, about 77s after recovery. It cannot be directly attributed to deletion.
Attempt 3 had 240 calls/endpoint and no failures. No successful response snapshot
mismatch was observed. JSONL UTC is request start, not continuous-outage evidence.

## Final verification and limits

Through the Helm Service from the fixed dashboard, all summary/metrics/ordered
events matched the new snapshot and unknown-ID endpoints returned 404. Final API
9dltm/xbk64 Ready, zero restarts; dashboard/DB unchanged, PVC Bound, PV
pvc-5b243a9e-ec4c-4f0a-a87e-2650a639b1dd; release remained revision 7. Deletion did
not change image tag or release history. No hard kill, node failure, DB failure,
in-flight POST, performance, or cluster recovery test; no zero-downtime/production-HA claim.

[Checked summary](../../artifacts/day22/checked-summary.json),
[before snapshot](../../artifacts/day22/before-run.json),
[final verification](../../artifacts/day22/after-verify.txt),
[attempt 1](../../artifacts/day22/attempt1-probe.jsonl),
[attempt 2](../../artifacts/day22/attempt2-probe.jsonl), and
[attempt 3](../../artifacts/day22/attempt3-probe.jsonl) retain evidence, with timing
and resource files alongside them. No program/chart changes or full Pytest rerun.
Progress 22/30 (73.3%); Day 23 later organized deployment handoff and regression.
