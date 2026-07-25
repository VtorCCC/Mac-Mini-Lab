"""Storage: a tiny SQLite helper that records when tasks run.

We keep this deliberately small. Each method opens a short-lived connection,
does its work, and closes it. That's simple and safe when the scheduler runs
jobs on background threads (a single shared connection would need extra care).

The one table, ``task_runs``, is what the health_check task counts to answer
"how many tasks ran in the last 24 hours?".
"""
from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

# The SQL that creates our table if it isn't there yet.
_SCHEMA = """
CREATE TABLE IF NOT EXISTS task_runs (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    task_name   TEXT    NOT NULL,
    started_at  TEXT    NOT NULL,   -- ISO-8601 UTC, e.g. 2026-07-21T08:00:00+00:00
    finished_at TEXT,               -- ISO-8601 UTC, or NULL if it never finished
    status      TEXT    NOT NULL,   -- 'success' or 'error'
    error       TEXT                -- the error message when status = 'error'
);
"""


class Storage:
    """Reads and writes the task-run history in a SQLite database file."""

    def __init__(self, db_path: Path | str) -> None:
        self.db_path = Path(db_path)
        # Make sure the containing folder (data/) exists.
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    def _connect(self) -> sqlite3.Connection:
        """Open a new connection to the database file."""
        return sqlite3.connect(self.db_path)

    def init_db(self) -> None:
        """Create the task_runs table if it doesn't already exist."""
        with self._connect() as conn:
            conn.executescript(_SCHEMA)

    def record_run(
        self,
        task_name: str,
        started_at: datetime,
        finished_at: datetime,
        status: str,
        error: str | None = None,
    ) -> None:
        """Save one completed (or failed) task run to the database."""
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO task_runs "
                "(task_name, started_at, finished_at, status, error) "
                "VALUES (?, ?, ?, ?, ?)",
                (
                    task_name,
                    started_at.astimezone(timezone.utc).isoformat(),
                    finished_at.astimezone(timezone.utc).isoformat(),
                    status,
                    error,
                ),
            )

    def count_runs_last_24h(self) -> int:
        """How many task runs were recorded in the last 24 hours."""
        cutoff = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
        with self._connect() as conn:
            # ISO-8601 UTC strings sort chronologically, so a plain >= works.
            cursor = conn.execute(
                "SELECT COUNT(*) FROM task_runs WHERE started_at >= ?",
                (cutoff,),
            )
            (count,) = cursor.fetchone()
        return int(count)
