"""PostgreSQL storage for completed simulation results."""

import psycopg
from psycopg.types.json import Jsonb

from app.services.run_store import (
    RunAlreadyExists,
    RunStoreError,
    RunStoreUnavailable,
    StoredRun,
)


class PostgresRunStore:
    """Persist completed simulation results in PostgreSQL."""

    def save(self, run: StoredRun) -> None:
        summary = run.summary.model_dump(mode="json")
        metrics = run.metrics.model_dump(mode="json")
        events = [event.model_dump(mode="json") for event in run.events]

        try:
            with psycopg.connect(connect_timeout=5) as connection:
                with connection.cursor() as cursor:
                    cursor.execute(
                        """
                        INSERT INTO completed_runs (run_id, summary, metrics, events)
                        VALUES (%s, %s, %s, %s)
                        """,
                        (
                            run.summary.run_id,
                            Jsonb(summary),
                            Jsonb(metrics),
                            Jsonb(events),
                        ),
                    )
        except psycopg.errors.UniqueViolation as exc:
            raise RunAlreadyExists("Run already exists") from exc
        except psycopg.OperationalError as exc:
            raise RunStoreUnavailable("Result storage is unavailable") from exc
        except psycopg.Error as exc:
            raise RunStoreError("Failed to save completed result") from exc
