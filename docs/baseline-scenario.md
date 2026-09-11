# Hand-Calculated Baseline Scenario

## Purpose

This scenario provides a manually verified acceptance test for the first
deterministic FabFlow simulation engine. Before more machines, random failures,
or AMHS behavior are introduced, the simulator must reproduce this scenario's
event order and KPI values.

## Scope

The baseline intentionally models the smallest useful production system:

- One process stage
- One machine with capacity one
- Three lots
- FIFO dispatching
- Deterministic processing times
- No setup or maintenance time
- No machine failures
- No transport or stocker delay
- All values expressed in abstract simulation-time units

## Initial Conditions

- The simulation begins at time `0`.
- The machine is idle and available at time `0`.
- A lot enters the FIFO queue at its arrival time.
- The machine immediately selects the oldest eligible waiting lot when idle.
- Ties are resolved by ascending `lot_id`.
- Processing is non-preemptive.
- A completion at time `t` frees the machine at time `t`.

## Input

| Lot | Priority | Arrival Time | Processing Time | Due Date |
| --- | --- | ---: | ---: | ---: |
| `LOT-001` | Normal | 0 | 10 | 20 |
| `LOT-002` | Normal | 2 | 5 | 20 |
| `LOT-003` | Normal | 4 | 8 | 30 |

## Manual Event Timeline

| Time | Event | Lot | Explanation |
| ---: | --- | --- | --- |
| 0 | `LOT_ARRIVED` | `LOT-001` | First lot enters the system |
| 0 | `LOT_QUEUED` | `LOT-001` | Lot enters the FIFO queue |
| 0 | `PROCESS_STARTED` | `LOT-001` | Machine is idle, so processing starts immediately |
| 2 | `LOT_ARRIVED` | `LOT-002` | Second lot enters while the machine is busy |
| 2 | `LOT_QUEUED` | `LOT-002` | Second lot waits in the FIFO queue |
| 4 | `LOT_ARRIVED` | `LOT-003` | Third lot enters while the machine is busy |
| 4 | `LOT_QUEUED` | `LOT-003` | Third lot waits behind `LOT-002` |
| 10 | `PROCESS_COMPLETED` | `LOT-001` | Ten processing units have elapsed |
| 10 | `LOT_COMPLETED` | `LOT-001` | The only route step is complete |
| 10 | `PROCESS_STARTED` | `LOT-002` | It is the oldest waiting lot |
| 15 | `PROCESS_COMPLETED` | `LOT-002` | Five processing units have elapsed |
| 15 | `LOT_COMPLETED` | `LOT-002` | The only route step is complete |
| 15 | `PROCESS_STARTED` | `LOT-003` | It is now first in the queue |
| 23 | `PROCESS_COMPLETED` | `LOT-003` | Eight processing units have elapsed |
| 23 | `LOT_COMPLETED` | `LOT-003` | All work is complete |

## Per-Lot Results

Definitions:

```text
waiting_time = processing_start_time - arrival_time
cycle_time = completion_time - arrival_time
tardiness = max(0, completion_time - due_date)
```

| Lot | Queue Entry | Start | Finish | Waiting Time | Cycle Time | Tardiness | On Time |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| `LOT-001` | 0 | 0 | 10 | 0 | 10 | 0 | Yes |
| `LOT-002` | 2 | 10 | 15 | 8 | 13 | 0 | Yes |
| `LOT-003` | 4 | 15 | 23 | 11 | 19 | 0 | Yes |

## Expected KPIs

### Completed Lots

```text
completed_lots = 3
```

### Makespan

```text
makespan = last_completion_time - simulation_start_time
         = 23 - 0
         = 23
```

### Throughput

For this baseline, throughput uses the makespan as its observation window:

```text
throughput = completed_lots / makespan
           = 3 / 23
           = 0.1304347826 lots per time unit
```

### Average Waiting Time

```text
average_waiting_time = (0 + 8 + 11) / 3
                     = 19 / 3
                     = 6.3333333333
```

### Average Cycle Time

```text
average_cycle_time = (10 + 13 + 19) / 3
                   = 42 / 3
                   = 14.0
```

### P95 Cycle Time

The baseline acceptance test uses the nearest-rank definition. For three
observations, the rank is:

```text
ceil(0.95 * 3) = 3
```

Sorted cycle times are `[10, 13, 19]`, therefore:

```text
p95_cycle_time = 19
```

### Machine Utilization

```text
machine_busy_time = 10 + 5 + 8
                  = 23

machine_available_time = 23

machine_utilization = machine_busy_time / machine_available_time
                    = 23 / 23
                    = 1.0
                    = 100%
```

### On-Time Delivery Rate

All three lots finish on or before their due dates:

```text
on_time_delivery_rate = on_time_lots / completed_lots
                      = 3 / 3
                      = 1.0
                      = 100%
```

### Final WIP

At the end of the scenario, all arrived lots are complete:

```text
final_wip = arrived_lots - completed_lots
          = 3 - 3
          = 0
```

## Expected Machine State Intervals

| Start | End | State | Active Lot |
| ---: | ---: | --- | --- |
| 0 | 10 | Processing | `LOT-001` |
| 10 | 15 | Processing | `LOT-002` |
| 15 | 23 | Processing | `LOT-003` |

The machine has no idle interval within the observation window `[0, 23]`.

## Acceptance Criteria

The first deterministic simulation is accepted only when it satisfies all of
the following:

1. The lot processing order is `LOT-001`, `LOT-002`, `LOT-003`.
2. Processing starts occur at times `0`, `10`, and `15`.
3. Lot completions occur at times `10`, `15`, and `23`.
4. Each lifecycle event is recorded exactly once.
5. No WIP, queue depth, waiting time, or cycle time is negative.
6. The final WIP and queue depth are both zero.
7. Integer-valued results match exactly.
8. Calculated floating-point KPIs match expected values within `1e-9`.
9. Repeated executions with the same configuration produce identical events
   and KPIs.

## Planned Automated Test Mapping

| Test | Assertion |
| --- | --- |
| `test_fifo_processing_order` | Completed lot IDs match the expected FIFO order |
| `test_baseline_event_timestamps` | Start and completion timestamps match the manual timeline |
| `test_baseline_waiting_times` | Waiting times equal `0`, `8`, and `11` |
| `test_baseline_cycle_times` | Cycle times equal `10`, `13`, and `19` |
| `test_baseline_kpis` | Aggregate KPIs match the hand calculations |
| `test_baseline_is_deterministic` | Two identical runs produce identical outputs |

## Interpretation

The baseline machine has 100% utilization, but two lots still experience
substantial waiting time. This illustrates an important manufacturing
trade-off: high machine utilization does not guarantee short lot cycle time.

Future experiments will change machine capacity, dispatching policy, failures,
and transport constraints while keeping scenario inputs and random seeds
controlled.
