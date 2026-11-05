# Day 2: Docker Baseline Verification

Status: Core acceptance complete, based on learner-provided terminal output and UI
confirmation. Planned date: October 30, 2026; estimate: 3 hours; actual hours unrecorded.
This belongs to the Kubernetes 30-day plan, not Day 2 of the original MVP.

## Goal and sequence

Redraw the Day 1 creation/query paths, inspect Dockerfile and Compose, start the
stack, run HTTP smoke checks, and exercise both dashboard presets. The planned
sequence allocated 15 minutes to architecture, 25 to configuration, 45 to startup,
30 to HTTP checks, 35 to UI checks, and 30 to documentation and shutdown.

Run commands from the repository root with Docker running and ports 8000/8501
available. Record date, commit, working-tree changes, OS/architecture, Docker
client/server, Compose, Python versions, image IDs, run IDs, and screenshots when
available. A first build downloads base images and dependencies.

At this milestone the API had one worker and stored results in process memory.
The browser used localhost:8501; dashboard Python used http://api:8000 on the
Compose network. Dockerfile defined separate API/dashboard targets; Compose
configured networking, published ports, environment variables, health checks,
and service_healthy startup dependencies. Image construction and container
execution are separate steps.

## Acceptance

| Scenario (FIFO, aging 60 minutes) | Lots | Finish (min) | Average cycle (min) | Transport jobs |
| --- | ---: | ---: | ---: | ---: |
| Three-stage baseline | 20 | 175 | 70.50 | 0 |
| AMHS bottleneck | 20 | 203 | 142.75 | 40 |

Both services were healthy and readiness returned ready. Learner-provided smoke
output passed dashboard health/HTML, API readiness, and both create/summary/metrics/
events workflows. The command exit code was not separately supplied. HTTP smoke
does not click browser buttons. The learner separately confirmed Check connection,
Run simulation, Load KPIs, and Refresh KPIs for both presets with the expected KPIs.
No run IDs or screenshots were supplied or claimed archived.

## Environment and troubleshooting

Client: macOS darwin/arm64; server: linux/arm64; Docker context: desktop-linux.
Docker client/Engine: 29.7.2; Desktop: 4.87.0; Compose: v5.4.0. Container Python
versions, commit, image IDs, date, and actual hours were not supplied.
An invalid docker show command was corrected to docker context show. No other
problem was reported. Shutdown was documented but execution was not confirmed;
at this milestone shutdown discarded API memory results.

Read logs before changing configuration. Check Docker startup, port conflicts,
downloads, and the dashboard API URL; see the [runbook](../runbook.md).

## Architecture review

The learner explained restart data loss and cross-process 404 responses: each
API process owns a separate dictionary, and a replacement Pod cannot recover it.
POST waits for synchronous simulation; GET reads saved results without rerunning.
Container localhost refers to that container, not the host or another service.
Health checks, HTTP workflow tests, and UI acceptance cover different behavior.

Deployment, Service, readiness, liveness, and future PostgreSQL storage were
introduced conceptually. Readiness removes an unready Pod from normal new Service
traffic without restarting it; liveness can restart the container. PostgreSQL can
share completed results but cannot automatically resume a simulation. No Kubernetes
verification occurred here. Instruction was paused at the learner's request before
Day 3, which later established the local cluster.

## Recorded commands and examples

These blocks preserve the milestone procedures and recorded output in their original
order. They describe the historical configuration; review current manifests and
prerequisites before repeating them. Resource names and IP addresses are observations,
not fixed values.

```bash
mkdir -p artifacts/k8s/day02
date -Iseconds
git rev-parse HEAD
git status --short
docker version
docker compose version
docker context show
docker compose config --quiet
```

```bash
docker compose up --build --wait --wait-timeout 120
docker compose ps
docker compose images
docker compose exec -T api python --version
docker compose exec -T dashboard python --version
curl --fail-with-body http://127.0.0.1:8000/health/ready
docker compose exec -T dashboard python - < scripts/smoke_containers.py > artifacts/k8s/day02/http-smoke.log 2>&1
```

```bash
docker compose ps
docker compose logs --no-color --tail=200 api dashboard > artifacts/k8s/day02/compose.log 2>&1
```

```bash
docker compose down
```

```text
PASS: Three-stage baseline; finish=175, cycle=70.5, transport_jobs=0
PASS: AMHS bottleneck; finish=203, cycle=142.75, transport_jobs=40
PASS: dashboard health/HTML, API readiness, and both create/query/metrics/events workflows
```

```text
Mac browser → localhost:8501 → Dashboard container
                                   ↓ http://api:8000
                                API container
                                   ↓
                        Synchronous simulation -> in-memory results
```
