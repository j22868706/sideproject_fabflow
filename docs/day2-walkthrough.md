# Day 2: Three-Stage Simulation

## 1. Scenario inputs

`simulator/scenarios/baseline.py` builds Lithography (10 minutes), Etching
(8 minutes), and Inspection (5 minutes). There are two Lithography machines
and one machine at each other station, each with capacity one. Lots arrive
every three minutes. The factory defaults to five lots and accepts
`number_of_lots=20` for the demo. The seed defaults to 42.

## 2. Create the runtime

Create `SimulationEngine(seed=scenario.seed)` and call `run_scenario(scenario)`.
The engine creates machines bound to its own SimPy environment and copies lots
so the scenario remains reusable. Each engine executes only once. The original
`run(lots, machine, queue)` interface remains supported and mutates its input lots.
Missing eligible groups, unprocessed-route violations, duplicate lot IDs, foreign
machine environments, and mismatched scenario seeds are rejected.

## 3. Arrival and route progression

Each lot waits until its arrival time, then records `LOT_ARRIVED` once. For each
route step it queues, obtains an eligible machine, processes for the step's
fixed duration, and increments `current_step`. `started_at` records only the
first processing start. `LOT_COMPLETED` and `completed_at` are set only after
all steps finish. Transport between stations takes zero time in Day 2.

## 4. Queue and capacity

Each machine group has one FIFO queue and a SimPy Store of available machine
slots. A machine contributes as many slots as its capacity; each assigned lot
also holds that machine's SimPy Resource for its processing duration. Slots
return after completion. Equal-time requests follow deterministic SimPy/input
order. Both Normal and Hot lots use FIFO until Day 3 introduces dispatch policies.

`active_lots` tracks every lot on a machine; `current_lot` exposes its first active
lot for compatibility. A machine stays BUSY while any active lot remains.
`busy_time` sums processing durations across slots, so for capacity greater than
one it is slot-minutes, not wall-clock busy time. Future utilization calculations
must divide by capacity times the observation duration.

## 5. Event trace

Each lot records arrival, then QUEUED / PROCESS_STARTED / PROCESS_COMPLETED for
each step, then one final completion. Queue and process events contain `step_id`;
process events also identify the selected machine. Queue depth reflects the
state immediately after enqueue or dequeue. A three-step lot has 11 events.

## 6. Execute the demo

Use a Python 3.12 environment with `python -m pip install -e ".[dev]"`, then:

```bash
python -m app.simulation.demo
```

```text
Completed lots: 20
Average cycle time: 70.5 minutes
Throughput: 6.86 lots/hour
```

Cycle time is completion minus arrival. Throughput is completed count divided
by elapsed hours over [0, final completion]. Here the last completion is at
175 minutes. Values are computed from simulation results, not the example
numbers in Guideline.txt. Processing is deterministic; the engine-owned random
generator is reserved for later stochastic behavior.

## 7. Verify

```bash
ruff check .
ruff format --check .
pytest -v
```

`tests/test_multistage.py` checks the five-lot hand calculation: completions at
23, 31, 39, 47, and 55 minutes, with average cycle time 33 minutes. It checks route
order, timestamps, capacity at every event, machine-group eligibility, BUSY state
with overlapping processing, empty final queues, repeated-scenario isolation,
FIFO ties, and the original documented single-station baseline. Existing tests
continue to cover the single-machine compatibility interface.

The next increment implements FIFO/SPT/Critical Ratio policy interfaces, Hot lot
selection, failure/repair, and the remaining KPI calculations.
