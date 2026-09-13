# Day 3 policy comparison

Scenario: `day3-policy-comparison` · Seed: 42 · Lots: 12

Synthetic inputs; each policy uses fresh lots and the same machine failure streams.
Observation window: time 0 through each policy's last completion. Times are minutes.
Hot lots take priority; Normal lots waiting at least 60 minutes take precedence in station FIFO order.

| Policy | Finish | Avg cycle | P95 cycle | Lots/hour | Avg WIP | Avg wait/lot | Avg queue | Peak queue | On time | Avg tardiness |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| FIFOPolicy | 89.90 | 39.77 | 69.90 | 8.01 | 5.31 | 26.19 | 3.50 | 9 | 41.7% | 10.95 |
| SPTPolicy | 82.74 | 36.37 | 71.74 | 8.70 | 5.28 | 22.81 | 3.31 | 9 | 50.0% | 9.00 |
| CriticalRatioPolicy | 82.74 | 40.21 | 66.74 | 8.70 | 5.83 | 26.65 | 3.87 | 9 | 41.7% | 10.31 |

## Machine metrics

| Policy | Machine | Utilization | Availability | Downtime |
| --- | --- | ---: | ---: | ---: |
| FIFOPolicy | LITHO-01 | 83.4% | 95.8% | 3.74 |
| FIFOPolicy | ETCH-01 | 66.7% | 98.8% | 1.09 |
| FIFOPolicy | INSPECT-01 | 26.7% | 100.0% | 0.00 |
| SPTPolicy | LITHO-01 | 90.6% | 95.5% | 3.74 |
| SPTPolicy | ETCH-01 | 72.5% | 98.9% | 0.92 |
| SPTPolicy | INSPECT-01 | 29.0% | 100.0% | 0.00 |
| CriticalRatioPolicy | LITHO-01 | 90.6% | 95.5% | 3.74 |
| CriticalRatioPolicy | ETCH-01 | 72.5% | 98.9% | 0.92 |
| CriticalRatioPolicy | INSPECT-01 | 29.0% | 100.0% | 0.00 |

## Observations

Lowest average cycle time: SPTPolicy. Highest on-time delivery rate: SPTPolicy (first policy shown if tied).
These are results for one synthetic workload and seed, not a general ranking.
Different finish times expose policies to different lengths of the same failure calendars.

P95 uses the nearest-rank method. WIP and total queue depth are time averages.
Waiting excludes time paused on a failed machine. Utilization is productive slot-minutes
divided by capacity × observation time; availability excludes machine downtime.
