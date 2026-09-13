# Day 3: Reliability, KPIs and comparison

## Reliability model

`MachineConfig.reliability` optionally accepts `ReliabilityConfig`. By default,
machines never fail, preserving the original baseline.

```python
from dataclasses import replace

from simulator.engine import SimulationEngine
from simulator.entities.reliability import ReliabilityConfig
from simulator.scenarios.baseline import create_baseline_scenario

scenario = create_baseline_scenario()
scenario = replace(
    scenario,
    machines=tuple(
        replace(machine, reliability=ReliabilityConfig(mtbf=40, mttr=3))
        for machine in scenario.machines
    ),
)
result = SimulationEngine(scenario.seed).run_scenario(scenario)
print(result.kpis)
```

For hand calculations, use `ReliabilityConfig(outages=((3, 4), (20, 2)))`:
fail at minute 3 for 4 minutes, then at minute 20 for 2 minutes. Fixed outages
must be ordered and non-overlapping; they cannot be combined with MTBF/MTTR.
Random parameters must both be positive and finite.

Random uptime and repair durations follow exponential distributions with means
MTBF and MTTR. Uptime is calendar time while the machine is operational,
including idle time; the next uptime starts after repair. Each configured machine
gets its own random stream seeded by the engine-owned RNG, in sorted machine-ID
order. Identical scenarios and seeds therefore share failure calendars across
policies, independent of dispatch order. Changing machine configuration can
change stream assignment. Processing times remain fixed.

A failure sets the entire machine to `DOWN`, prevents new starts, and pauses all
active slots. Repair resumes remaining work without scrapping or restarting lots.
Lots paused on a machine retain their resources and `PROCESSING` status. Their
pause time contributes to cycle time, but not queue waiting or productive busy
time. Each operation still emits one start and one completion. Machine events
`MACHINE_FAILED` and `MACHINE_REPAIRED` have `lot_id=None`.

Events at the same timestamp use SimPy event order. An operation whose processing
time is fully consumed can finish at a failure boundary. The run stops when all
lots complete, even if an idle machine is down or future failures are scheduled.
Final machine status can consequently be `DOWN`. KPI downtime clips an unfinished
repair to the observation end. `Machine.downtime` tracks fully finished repairs;
use `result.kpis.machines` for observation-window downtime and availability.

## KPI definitions

All runs finish all lots. The observation window is `[0, finished_at]`, including
any idle time before the first arrival. Times are minutes; rates and utilization
fractions are unrounded in Python/JSON.

| Field | Definition |
| --- | --- |
| `average_cycle_time` | Mean of completion minus arrival |
| `p95_cycle_time` | Sorted cycle time at rank `ceil(0.95 * lot_count)` |
| `throughput_per_hour` | Completed lots × 60 / observation minutes |
| `average_wip` | Sum of cycle times / observation minutes; time-average arrived, unfinished lots |
| `average_waiting_time` | Total queue wait across all operations / lot count |
| `average_queue_depth` | Total queue wait / observation minutes; sum across all station queues |
| `max_queue_depth` | Peak total queued lots in event order, including instantaneous queue transitions |
| `on_time_delivery_rate` | Fraction completing at or before due date |
| `average_tardiness` | Mean `max(0, completion - due_date)` over all lots |
| Machine `utilization` | Productive slot-minutes / (capacity × observation minutes) |
| Machine `availability` | 1 − clipped downtime / observation minutes |

Empty results return zero lot KPIs. Machine availability for a zero-length
window is defined as 1, and utilization as 0. Machine capacity and productive
busy time are copied into immutable result summaries. KPIs are available through
`result.kpis`; existing `average_cycle_time` and `throughput_per_hour` remain.
Transport and delivery-time accuracy await the AMHS model.

## Generate the comparison report

```bash
python -m app.simulation.compare
python -m app.simulation.compare --seed 42 \
  --output docs/day3-comparison-report.md \
  --json /tmp/fabflow-day3-comparison.json
```

The CLI runs FIFO, SPT and CR on fresh copies of a 12-lot three-stage scenario
with heterogeneous operation times and due dates, including three Hot lots.
Use `--normal-wait-threshold 30` to change the default 60-minute Normal aging
threshold. The threshold is recorded in both Markdown and JSON. Markdown includes aggregate
and per-machine KPIs; JSON contains scenario inputs, complete events, completion
orders and unrounded metrics. The generated sample is in
[Day 3 comparison report](day3-comparison-report.md).

Policies can finish at different times, exposing them to different lengths of
the same failure calendar. This is a finite-workload comparison, not a common
fixed-horizon experiment. One seed does not establish a universal winning policy.

## Validation

Behavioral tests cover repeated interruptions, multi-slot pauses, idle failures,
healthy peer dispatch, repeatability, shared calendars, final downtime clipping,
invalid reliability inputs, hand-calculated KPIs, empty results, and CLI exports.
The original no-failure baselines remain regression tests.
