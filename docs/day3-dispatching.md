# Day 3: Dispatching policies

The engine accepts a policy object and applies it across all machine groups.
Existing callers use FIFO by default, including the single-machine `run()` API.

```python
from simulator.engine import SimulationEngine
from simulator.policies.critical_ratio import CriticalRatioPolicy
from simulator.policies.fifo import FIFOPolicy
from simulator.policies.spt import SPTPolicy
from simulator.scenarios.baseline import create_baseline_scenario

scenario = create_baseline_scenario(seed=42, number_of_lots=20)
for policy in (FIFOPolicy(), SPTPolicy(), CriticalRatioPolicy()):
    result = SimulationEngine(scenario.seed, policy=policy).run_scenario(scenario)
    print(type(policy).__name__, result.average_cycle_time, result.throughput_per_hour)
```

Each run copies scenario lots. Use a fresh engine for each policy. The baseline
has uniform operation durations per station, so SPT can produce the same order
as FIFO; distinct policy behavior is tested with heterogeneous durations and dues.

## Ranking rules

| Policy | Primary rank (lowest first) |
| --- | --- |
| FIFO | Time the lot entered this station queue |
| SPT | Processing time of the current operation |
| Critical Ratio | `(due_date - current_time) / remaining_processing_time` |

Remaining processing time includes the current operation and all subsequent
operations, excluding completed operations. CR is recalculated at every dispatch;
overdue lots have negative ratios. A candidate must have remaining work.
SPT and CR ties use station queue entry time, then an engine-assigned enqueue
sequence. FIFO also uses that sequence for equal entry times. These base policy
classes rank candidates supplied to them; the engine wraps them in `HotLotPolicy`.

## Hot lot insertion and Normal lot aging

At every free-slot decision, the engine selects in this order:

1. Normal lots whose station wait is at least `normal_wait_threshold`, in FIFO order.
2. Hot lots ranked by the selected FIFO, SPT, or CR policy.
3. Remaining Normal lots ranked by the selected policy.

The default threshold is 60 minutes, a configurable synthetic modeling choice.
Use `SimulationEngine(seed=42, policy=SPTPolicy(), normal_wait_threshold=30.0)`
to change it. The value must be finite and positive. Waiting starts on entry to
each station, including repeated visits; it is not measured from fab arrival.
The wrapper never changes a lot's priority or interrupts active processing.

Aged Normal lots use FIFO so newer short or urgent lots cannot repeatedly bypass
them. The threshold grants dispatch precedence, not a guaranteed start deadline:
existing work, outages, and older aged lots can still delay service. This is a
basic starvation safeguard, not a general fairness scheduler. Hot lots themselves
do not receive an aging guarantee.

The hand-checked continuous-arrival test uses two-minute operations, a Normal lot
arriving at minute 1, and Hot lots arriving every minute from 1.5 onward. With a
five-minute threshold, starts are blocker at 0, Hot at 2, Hot at 4, Normal at 6.
It verifies service while Hot arrivals continue for all three base policies,
as well as queue state, completion counts, and repeatability.

## Dispatch lifecycle

A lot joins its current machine-group queue and waits for an assignment. One
station dispatcher acquires an available capacity token, selects a candidate,
and wakes that lot's process. Each token belongs to a real eligible machine;
processing still uses its SimPy resource. Completion returns the token and the
lot continues to its next operation or completes. Processing is non-preemptive.

Decisions consider candidates enqueued when the dispatcher resumes with a free
slot. Events sharing a timestamp follow deterministic SimPy scheduling order;
the engine does not batch all events at that timestamp into a single decision.
Policies receive a tuple of candidates and must return one of those objects
without modifying lots or the queue.

## Hand-checkable policy example

One machine processes a blocker from time 0 to 10. While it is busy, lots enter:

| Lot | Arrival | Processing time | Due date |
| --- | --- | --- | --- |
| long | 1 | 6 | 100 |
| short | 2 | 2 | 100 |
| urgent | 3 | 4 | 8 |

After the blocker, FIFO selects long → short → urgent (starts 10, 16, 18),
SPT selects short → urgent → long (starts 10, 12, 16), and CR selects
urgent → long → short (starts 10, 14, 20). All finish at time 22.

Tests cover these timestamps and queue depths, current-operation SPT ranking,
remaining-route CR ranking, time-dependent and overdue CR decisions, FIFO ties,
empty queues, repeatability, capacity, and repeated visits to the same station.
The original multi-stage and single-machine baselines remain regression tests.

Equipment failure/repair and KPI reports are implemented; see
[Day 3 reliability and KPIs](day3-reliability-kpi.md).
