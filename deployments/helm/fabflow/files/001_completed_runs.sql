CREATE TABLE completed_runs (
    run_id text PRIMARY KEY,
    summary jsonb NOT NULL CHECK (jsonb_typeof(summary) = 'object'),
    metrics jsonb NOT NULL CHECK (jsonb_typeof(metrics) = 'object'),
    events jsonb NOT NULL CHECK (jsonb_typeof(events) = 'array'),
    created_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CHECK (summary ->> 'run_id' IS NOT NULL AND summary ->> 'run_id' = run_id)
);
