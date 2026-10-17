# Reproducible FabFlow demo

This sequence demonstrates manufacturing simulation, transport congestion, and
dispatch-policy trade-offs using synthetic data. Allow about 5–10 minutes after
initial setup. Follow the [runbook](runbook.md) to start the API and dashboard
first. These are finite-workload experiments; the results are not production-fab
benchmarks or universal policy rankings.

## 1. Connect and run the manufacturing baseline

Open http://localhost:8501. Select **Check connection** and expect
**API is ready to accept simulations.** For Compose, leave the API address as
`http://api:8000`; for local Python, use `http://127.0.0.1:8000`.

Set the form to:

| Field | Value |
| --- | --- |
| Scenario | Three-stage baseline |
| Dispatch policy | FIFO |
| Normal lot aging threshold (minutes) | 60 |

Select **Run simulation**, then **Load KPIs**. Explain that 20 lots compete for
shared station queues across three operations. Simulation time is measured in
minutes; finish time is simulated time, not server execution duration.

| Visible result | Expected value |
| --- | ---: |
| Completed lots | 20 |
| Simulation finish time | 175 min |
| Average cycle time | 70.50 min |
| P95 cycle time | 113.00 min |
| Throughput | 6.86 lots/hour |
| On-time delivery | 65.0% |
| Etching utilization | About 91.43% |

Equipment availability is 100% because this preset has no failures. Utilization
can be lower: an available machine need not be processing a lot. The AMHS section
reports no transport jobs because this preset uses instantaneous transfers.

Select **Refresh KPIs**. The run ID and values remain the same; this action reads
existing results rather than running another simulation.

## 2. Show transport congestion

Choose **AMHS bottleneck**, keep FIFO and the 60-minute threshold, and select
**Run simulation**. A new run ID appears and its KPIs must be loaded separately.
Select **Load KPIs** and show:

| Visible result | Expected value |
| --- | ---: |
| Completed lots | 20 |
| Simulation finish time | 203 min |
| Average cycle time | 142.75 min |
| P95 cycle time | 198.00 min |
| Throughput | 5.91 lots/hour |
| On-time delivery | 45.0% |
| Transport jobs | 40 |
| Vehicle utilization | 98.5% |
| Average wait for vehicle | 53.375 min/job (about 53.38) |
| Average travel time | 5 min/job |

One shared vehicle serves two transfers per lot. Point to the waiting/travel
chart: waiting exceeds actual travel time. The baseline and AMHS presets also
have different arrivals, machines, and operation durations, so comparing these
two pages alone does not isolate the effect of enabling AMHS.

To isolate vehicle capacity on the same AMHS workload, use an activated local
Python environment with the project installed:

```bash
python -m app.simulation.amhs --output /tmp/fabflow-amhs.md --json /tmp/fabflow-amhs.json
```

| Vehicles | Average transport wait (min/job) | Average cycle (min) | Lots/hour |
| ---: | ---: | ---: | ---: |
| 1 | 53.38 | 142.75 | 5.91 |
| 3 | 2.62 | 57.05 | 12.90 |
| 6 | 0.00 | 55.00 | 12.90 |

Explain that three vehicles relieve congestion, while six do not further improve
throughput because Etching becomes the processing bottleneck. The dashboard
preset uses one vehicle; the paired capacity experiment runs through this CLI.

## 3. Demonstrate dispatch-policy trade-offs

The dashboard supports FIFO, SPT, and CR, but its two fixed-time presets may
produce the same KPI values across policies. Use the heterogeneous comparison
workload with varied processing times/due dates, Hot lots, and seeded failures:

```bash
python -m app.simulation.compare --seed 42 --normal-wait-threshold 60 \
  --output /tmp/fabflow-comparison.md --json /tmp/fabflow-comparison.json
```

Open `/tmp/fabflow-comparison.md`:

| Policy | Average cycle (min) | P95 cycle (min) | Lots/hour | On-time delivery |
| --- | ---: | ---: | ---: | ---: |
| FIFO | 39.77 | 69.90 | 8.01 | 41.7% |
| SPT | 36.37 | 71.74 | 8.70 | 50.0% |
| CR | 40.21 | 66.74 | 8.70 | 41.7% |

SPT has the lowest average cycle time in this experiment; CR has the lowest P95.
Policies share scenario inputs and failure calendars, and run until the workload
finishes. The finite observation windows differ. One scenario and seed do not
establish a universally best policy.

## 4. Show validation and API access

In the dashboard, change **API base URL** to `invalid-url`, commit the input,
and select **Check connection**. Expect an HTTP/HTTPS address validation message;
results from the previous address are hidden. Restore the original address and
select **Check connection**; the saved run is visible again in the same session.

For HTTP input validation, open http://localhost:8000/docs and submit
[the baseline request](examples/baseline.json) to `POST /api/v1/runs` with
`policy` changed to `unknown`. Expect HTTP 422. Restore FIFO and expect HTTP 201.
Copy `run_id` into the summary, metrics, and events query endpoints. See the
[Swagger walkthrough](day5-api.md#step-4-full-workflow-acceptance-complete-locally)
for the detailed sequence.

## 5. Finish and preserve evidence

Before stopping, export metrics/events if needed using the [runbook](runbook.md).
For repeatable browser evidence, run `python scripts/smoke_browser.py` with the
browser extra installed. The screenshots show real synthetic simulation output;
run IDs change between runs. The browser script uses a 30-minute threshold, and
the walkthrough above uses 60; the displayed baseline/AMHS values above were
independently checked with FIFO and 60.

Stop Compose with `docker compose down`, or stop the two local terminals with
Ctrl+C. API results disappear when its process stops. See the
[portfolio summary](portfolio.md) for the selected screenshots and project description.
