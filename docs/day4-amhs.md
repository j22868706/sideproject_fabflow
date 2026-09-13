# Day 4: simplified AMHS

Day 4 in `Guideline.txt` is implemented: transport jobs, finite SimPy resources,
transport queueing, manufacturing integration, KPIs, and vehicle-count experiments.

## Inputs and lifecycle

`SimulationScenario.transport` accepts `TransportConfig(vehicle_count=3, travel_time=5)`.
The count must be a positive integer; travel time must be finite and non-negative.
All times are minutes. `None` disables transportation and preserves Day 2/3 behavior.

After each operation except the last, the machine slot is released and the lot
requests an interchangeable vehicle from a shared `simpy.Resource`. Requests use
FIFO order, including Hot lots. The lot is `WAITING_FOR_TRANSPORT` until pickup,
then `IN_TRANSPORT` until delivery. Only then does it join the next station queue.
Station aging begins at that queue entry. Waiting and travel both contribute to
cycle time and WIP; neither contributes to station queue waiting or machine busy time.
Machine reliability continues independently while lots wait or travel.

There is one job per pair of adjacent route operations, including repeated visits
to the same group. There are no entry or exit moves. Origins and destinations are
machine-group IDs, since the next machine is selected only after delivery.

`result.transport_jobs` contains immutable completed records with `job_id`, `lot_id`,
`origin`, `destination`, `requested_time`, `pickup_time`, and `delivery_time`.
The corresponding events are `TRANSPORT_REQUESTED`, `TRANSPORT_STARTED`, and
`TRANSPORT_COMPLETED`, each carrying `transport_job_id`, origin, and destination.
Their `queue_depth` is the current number of waiting resource requests, excluding
allocated vehicles; requested events are recorded after submitting the request.
At equal timestamps, event order follows deterministic SimPy scheduling.

## KPI definitions

All metrics use the full observation window `[0, result.finished_at]`.

| Field on `result.kpis` | Definition |
| --- | --- |
| `average_transport_time` | Mean delivery minus pickup, per completed job |
| `average_transport_waiting_time` | Mean pickup minus request, per completed job |
| `vehicle_utilization` | Total loaded travel minutes / (vehicle count × observation minutes) |
| `transport_job_count` | Number of completed transport jobs |

Average request-to-delivery time is the sum of the two transport averages.
Utilization is the pooled fleet average, not a per-vehicle measurement. Disabled
transport or no jobs produces zero transport metrics; zero-duration travel is valid.

## Reproduce and verify

```bash
python -m app.simulation.amhs --output docs/day4-amhs-report.md --json /tmp/amhs.json
pytest -q tests/test_transport.py
```

The [generated report](day4-amhs-report.md) compares 1, 3, and 6 vehicles on identical
20-lot inputs with seed 42. Fixed travel and processing times and disabled failures
make this experiment deterministic without random sampling. The JSON contains
scenario parameters, all KPIs, transport jobs, and events.

A two-lot hand calculation in the tests uses one-minute operations and three-minute
travel: requests occur at minutes 1 and 2; pickups at 1 and 4; deliveries at 4 and 7;
lots complete at 5 and 8. Average transport waiting is 1 minute, fleet utilization
is 6/8, and average cycle time is 6.5 minutes. The second upstream operation finishes
at minute 2 while the first vehicle is occupied, verifying machine release.

Additional tests cover vehicle capacity and FIFO at each event, route/event order,
repeatability and input isolation, no-transport compatibility, zero-duration travel,
single-operation routes, repeated station visits, downstream outages, invalid inputs,
report exports, and the throughput plateau when Etching becomes the bottleneck.

## Simplifications

Vehicles have no position or individual ID. Travel is fixed for all station pairs;
empty repositioning, loading/unloading, path conflicts, vehicle failures, and stocker
capacity are omitted. Buffers are unbounded. There is no transport priority or route
optimization. These are finite-workload comparisons; utilization includes startup
and drain time. Low downstream utilization is evidence of lost processing opportunity,
but is not itself a dedicated starvation-duration metric or a universal bottleneck proof.

## Day 4 acceptance audit

| Guideline step | Implementation and verification | Status |
| --- | --- | --- |
| Hour 1: transport model | Immutable jobs record origin, destination, request, pickup, delivery | Complete |
| Hour 2: finite resources | SimPy Resource, FIFO queue, fixed travel time, delivery before station entry | Complete |
| Hour 3: AMHS KPIs | Travel time, waiting time, pooled utilization, job count; hand-calculated tests | Complete |
| Hour 4: congestion | 1/3-vehicle comparison, capacity and downstream idle-gap tests, cycle-time comparison | Complete |
| Completion criterion | 3/6-vehicle throughput plateau demonstrates the bottleneck moving to Etching | Complete |

The explicit downstream shortage test measures Etching idle gaps between its first
start and final completion, excluding initial startup and final drain. One vehicle
produces 44 minutes of gaps; three produce zero. For every gap, the test verifies
no intervening station queue arrivals and that processing resumes at the next
lot's transport delivery timestamp. This scenario has no failures or other causes
of machine unavailability.

Re-audit validation: Ruff lint and formatting pass, all 90 tests pass (15 AMHS tests),
and regenerated Markdown matches the checked-in report. Markdown/JSON export and
the Day 2 baseline and Day 3 policy comparison commands also run successfully.
Fixed travel time satisfies the guideline's fixed-or-random requirement. Stocker
capacity is explicitly optional and remains deferred. Day 5–7 are separate work.
