# Day 10: PostgreSQL Development Environment

Status: Configuration, connectivity acceptance, and guided review complete from
learner output. Actual hours unrecorded. RunService still used memory at this milestone.

## Configuration

Compose gained PostgreSQL 17 service db with database/user fabflow, named volume
postgres_data at /var/lib/postgresql/data, and a read-only init directory at
/docker-entrypoint-initdb.d. The ignored .env holds the local password; .env.example
contains only a placeholder. Compose rejects an empty POSTGRES_PASSWORD.
API uses PGHOST=db, PGPORT=5432, PGDATABASE/PGUSER=fabflow and PGPASSWORD.
psycopg[binary]>=3.2,<4.0 was added and the API image rebuilt. DB has no published
host port; use the Compose service name, not localhost. Environment configuration
alone does not switch application storage.

## Observed setup and schema

Compose v5.4.0 initially had no running containers. The learner corrected db nesting,
volumes mistakenly under environment, and the missing nonempty-password check.
After local .env creation, config validation passed, the image downloaded,
fabflow_postgres_data was created, and fabflow-db-1 started. pg_isready accepted
connections; SQL returned database/user fabflow. Container Up alone is insufficient.

The Day 9 schema was added after DB first start, so it did not automatically run
on the existing volume. A one-time psql invocation with ON_ERROR_STOP created
completed_runs. Inspection showed five NOT NULL fields, the primary key, three
JSON-shape constraints, and summary/key consistency. Initialization is for empty
data directories, not migration; do not rerun CREATE TABLE against an existing table.
After adding the mount and recreating the DB container, the SQL file was visible
and to_regclass returned completed_runs. No simulation rows were inserted, so
this verifies schema survival, not completed-result persistence. Empty-volume
automatic initialization was not separately tested here.

## API connectivity and secrets

The learner rebuilt API, initially health: starting (no final healthy output
supplied), and executed real psycopg queries inside it. Results were
('fabflow', 'fabflow') and ('completed_runs',), proving driver, network,
authentication, and table visibility, not RunStore save/get.

.env was confirmed ignored and absent from git status. A trailing whitespace issue
on postgres_data was reported fixed; the assistant also restored final newlines.
The learner understood init scripts do not rerun on populated data, container
replacement retains a separately retained volume, ordinary down preserves it,
and down -v deletes it. Volume deletion was not performed.
CI's disposable test DB received a test-only password so nonempty validation would
not break existing container checks; no real local credential was committed or
reported. README/runbook gained .env setup steps. Remote CI was not verified here.

## Verification and handoff

Assistant checks passed Ruff lint/format, pytest (179 passed, one upstream
TestClient/HTTPX deprecation warning), git diff --check, and Compose config --quiet
on the Python 3.14 host environment. Python 3.12 full tests, container HTTP smoke,
and browser acceptance were not rerun. A Day 9 example formatting gap was fixed.
Workbook Days 8–10 were pending at this point. A local DB/volume is not HA or
backup. Day 11 implemented complete-result writes and commit-before-201 behavior.

## Recorded commands and examples

These blocks preserve the milestone procedures and recorded output in their original
order. They describe the historical configuration; review current manifests and
prerequisites before repeating them. Resource names and IP addresses are observations,
not fixed values.

```bash
docker compose config --quiet
docker compose up -d db
docker compose ps db
docker compose exec db pg_isready -U fabflow -d fabflow
docker compose exec db psql -U fabflow -d fabflow \
  -c "SELECT current_database(), current_user;"
```

```bash
docker compose exec -T db psql -U fabflow -d fabflow \
  -v ON_ERROR_STOP=1 < deployments/postgres/init/001_completed_runs.sql
docker compose exec db psql -U fabflow -d fabflow -c '\d completed_runs'
```

```bash
docker compose exec db psql -U fabflow -d fabflow \
  -c "SELECT to_regclass('public.completed_runs');"
```

```bash
docker compose up -d --build api
docker compose ps api db
```

```bash
docker compose exec -T api python - <<'PY'
import psycopg

with psycopg.connect(connect_timeout=5) as conn:
    with conn.cursor() as cursor:
        cursor.execute("SELECT current_database(), current_user")
        print(cursor.fetchone())
        cursor.execute("SELECT to_regclass('public.completed_runs')")
        print(cursor.fetchone())
PY
```

```text
('fabflow', 'fabflow')
('completed_runs',)
```
