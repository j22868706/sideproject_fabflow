# FabFlow: semiconductor dispatching and AMHS simulator

FabFlow is a Python discrete-event simulator for exploring how dispatch decisions,
machine outages, and limited material-handling capacity affect a synthetic fab.
It connects a SimPy engine to a synchronous FastAPI service and Streamlit
dashboard, with Docker Compose and automated browser acceptance for a repeatable
local demonstration. The subsequent deployment track adds PostgreSQL persistence,
two API replicas on local Kubernetes, versioned Helm deployments, image-build CI,
and a separate Argo CD environment with manual synchronization.

## Problem and implemented scope

Wafer lots compete for processing capacity and transport vehicles. A faster
dispatch policy or additional vehicles can change average cycle time, tail
latency, delivery performance, and equipment utilization in different ways.
FabFlow makes those trade-offs observable through event records, KPI calculation,
and reproducible comparison experiments.

The implemented MVP supports three manufacturing stages, FIFO/SPT/Critical Ratio,
Hot lot priority with Normal lot aging protection, machine failure/repair, and a
shared FIFO AMHS vehicle pool. The API validates explicit scenario inputs and
exposes completed summaries, KPIs, and events. The dashboard submits two preset
scenarios and displays manufacturing, equipment, and transport metrics.

## Dashboard evidence

The images below are unmodified screenshots from the successful Day 6 real
browser acceptance run against the Python 3.12 Compose stack. They use FIFO,
seed 42, and a 30-minute Normal lot aging threshold. Playwright 1.64.0 drove
headless Google Chrome 155.0.8059.80 at a 1440 × 1100 viewport on October 17,
2026, against application commit `2d83879`. The third image is the chart element
capture produced by the same script. All data is synthetic.

### Manufacturing baseline

20 lots complete at simulated minute 175. The screen shows a 70.50-minute average
cycle time, 113.00-minute P95, 6.86 lots/hour, and 65.0% on-time delivery.
Separate equipment charts distinguish productive utilization from availability.

![Baseline manufacturing KPIs and equipment charts](images/three-stage-baseline-kpis.png)

### AMHS bottleneck

One shared vehicle serves 40 transport jobs. The run finishes at minute 203,
with a 142.75-minute average cycle time and 5.91 lots/hour. Equipment availability
is 100% in this no-failure preset even when utilization is low.

![AMHS workload KPIs and equipment charts](images/amhs-bottleneck-kpis.png)

Average waiting for a vehicle is 53.375 minutes per job, compared with five
minutes of travel. The chart exposes the transport queue contribution directly.

![Average AMHS travel and vehicle waiting time in minutes per job](images/amhs-bottleneck-chart.png)

These two dashboard presets have different workloads and processing resources;
their difference alone does not isolate the impact of enabling transportation.
Use the paired vehicle experiment below to evaluate vehicle capacity.

## Reproducible findings

| Experiment | Observed result | Scope |
| --- | --- | --- |
| FIFO/SPT/CR with seed 42 | SPT average cycle 36.37 min versus FIFO 39.77; CR P95 66.74 min versus SPT 71.74 | One 12-lot heterogeneous workload with shared failure calendars |
| One versus three AMHS vehicles | Average cycle 142.75 to 57.05 min; throughput 5.91 to 12.90 lots/hour | Same 20-lot workload and five-minute transfers |
| Three versus six vehicles | Throughput stays 12.90 lots/hour while average cycle drops to 55.00 min | Etching becomes the processing bottleneck |

These are simulator results, not measured improvements in a real fab. They
illustrate trade-offs for specific inputs rather than a universal policy ranking.
The [demo walkthrough](demo-walkthrough.md) includes commands, parameters, and
expected outputs; the [policy report](day3-comparison-report.md) and
[AMHS report](day4-amhs-report.md) retain the experiment details.

## Engineering decisions and verification

| Decision | Why it matters | Implementation |
| --- | --- | --- |
| Engine-owned random streams and fresh per-run entities | Keeps experiments repeatable and failure calendars comparable across policies | [Simulation engine](../simulator/engine.py) |
| Immutable event records and explicit KPI definitions | Makes lifecycle order and metric calculations inspectable | [Events](../simulator/events/event.py), [KPIs](../simulator/metrics/kpi.py) |
| Priority wrapper with Normal lot aging | Allows Hot insertion while protecting long-waiting Normal lots from starvation | [Dispatch wrapper](../simulator/policies/hot_lot.py) |
| Synchronous API with interchangeable memory/PostgreSQL stores | Commits complete results before success while retaining a simple local mode | [Run service](../app/services/runs.py), [PostgreSQL store](../app/services/postgres_run_store.py) |
| Dashboard as an HTTP client | Exercises the same API used by external clients and keeps simulation logic in the backend | [Dashboard](../app/dashboard/main.py) |
| Health-gated Compose startup and real browser checks | Verifies service connectivity and actual widget/chart behavior | [Compose](../compose.yaml), [browser acceptance](../scripts/smoke_browser.py) |

The fresh Python 3.12.14 verification passed 179 tests with 93% combined
statement/branch coverage across `app` and `simulator`. Ruff lint, formatting,
dependency consistency, and Compose configuration also passed. Both remote CI
jobs passed for `2d83879`, including real Chromium acceptance:
[verified workflow run](https://github.com/j22868706/sideproject_fabflow/actions/runs/39043904601).
The Day 7 handoff commit `9867659` also passed both jobs:
[successful delivery CI](https://github.com/j22868706/sideproject_fabflow/actions/runs/39044791273).

## Kubernetes and persistence evidence

| Capability | Accepted outcome | Evidence and limits |
| --- | --- | --- |
| Shared result storage | Two named API Pods independently return identical summary, metrics, and ordered events | [Cross-replica acceptance](k8s/day14-api-replicas.md); single DB and single node |
| DB outage handling | Both APIs return 503 during outage; retained results recover with original PVC | [Persistence acceptance](k8s/day15-persistence-acceptance.md); no database HA |
| Versioned deployment | Locally built ARM64 images loaded into kind; Helm uses explicit source SHA tags | [Deployment record](k8s/day19-versioned-deployment.md); CI builds but does not publish images |
| Rolling-update observation | 2,376 requests, 5 failures over 300 seconds; command duration 6.818 seconds | [Raw evidence and method](k8s/day20-rolling-update.md); full-window sample, unconfirmed cause, not zero downtime |
| API replacement | Three observed replica recoveries: 3.049 / 3.694 / 3.583 seconds; full-window failures 2 / 1 / 0 | [Recovery measurements](k8s/day22-pod-recovery.md); includes command/polling overhead, not HTTP downtime |
| GitOps | Manual tag synchronization, drift correction, and Git revert accepted | [GitOps record](k8s/day25-gitops-sync.md); no auto-sync/self-heal acceptance |

The [architecture report](k8s/day26-measurements-architecture.md) links original
measurement files and explains the Day 21 correction: its localhost integrity
checks reached Compose, so they are excluded from Helm rollback data evidence.
The [Day 27 demonstration](k8s/day27-readme-demo.md) records successful tag-switch
and rollback checks on both API Pods; its timed five-minute rehearsal is pending.

## Reuse in a project summary

This project used AI assistance for implementation, tests, debugging, and
documentation, with user-defined scope and milestone approvals. The results
above are supported by executed simulations and automated verification.

Built a reproducible semiconductor manufacturing simulator with Python, SimPy,
FastAPI, and Streamlit. Implemented dispatch policies, priority aging, equipment
failure/repair, AMHS capacity constraints, and event-based KPIs. Delivered a
Docker Compose demo validated by 179 tests and real browser workflows; used
paired synthetic experiments to show dispatch and transport bottleneck trade-offs.

Extended the service with PostgreSQL result persistence, two API replicas,
versioned Helm deployments on kind, and manual Argo CD synchronization. Verified
cross-Pod result consistency and database-outage recovery, and preserved raw HTTP
measurements for rolling updates and three API Pod replacement exercises.

## Demonstration and limits

Copy `.env.example` to ignored `.env` and set a local development password, then
run `docker compose up --build --wait --wait-timeout 120` and open
http://localhost:8501. Follow the [runbook](runbook.md) for dependencies, API
addresses, evidence generation, result exports, and shutdown.

The model uses synthetic inputs, fixed processing/travel times, and simplified
routing. It omits recipe qualification, setups, physical vehicle paths, and
stocker capacity. Unconfigured local Python execution stores results in process
memory; Compose/Kubernetes store completed results in PostgreSQL. In-flight
simulations have no checkpoint or automatic retry. All Kubernetes components
share one local node, PostgreSQL is a single instance, and its PVC is not a
backup or protection against cluster loss. There is no production performance,
zero-downtime, database-HA, or public-hosted-deployment claim.
Desktop Chrome and CI Chromium are verified;
mobile layouts and other browser engines have not been tested.

The three selected PNGs are tracked in `docs/images/` for GitHub viewing. Raw
browser traces and failure captures remain ignored under `artifacts/browser/`.
Regenerate evidence with `python scripts/smoke_browser.py` after installing the
browser extra; see [Day 6 acceptance](day6-dashboard.md#step-5-real-browser-acceptance-complete-locally).
