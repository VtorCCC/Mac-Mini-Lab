# 05 · SQLite storage (the run history)

## What is SQLite?

SQLite is a tiny database that lives in **a single file** — no server to install
or run. Perfect for a small project on one Mac. agent-hub's database is at
`data/agent-hub.db`, created automatically the first time you run the app.

## What we store

One table, `task_runs`, with one row per task run:

| Column | Meaning |
|--------|---------|
| `id` | An auto-incrementing row number |
| `task_name` | Which task ran (e.g. `health_check`) |
| `started_at` | When it started (ISO-8601, UTC) |
| `finished_at` | When it finished (ISO-8601, UTC) |
| `status` | `success` or `error` |
| `error` | The error message, if it failed |

This is written by `core/scheduler.py`'s guard **every** time a task runs, so
the table is a complete history of successes and failures.

## Why it exists

The `health_check` task answers "how many tasks ran in the last 24 hours?" by
counting rows in this table. More generally, it's your audit log: proof of what
ran and when, and a record of every failure.

## The code (it's small)

All of it is in [`core/storage.py`](../core/storage.py). The three methods:

- `init_db()` — creates the table if it doesn't exist (safe to call every start).
- `record_run(...)` — inserts one row.
- `count_runs_last_24h()` — counts rows newer than 24 hours ago.

Two beginner-friendly details worth understanding:

**1. New connection per operation.** Each method opens the file, does its work,
and closes it (via `with self._connect() as conn:`). This keeps things simple
and safe when tasks run on background threads.

**2. Times are stored as UTC text.** We save timestamps as ISO-8601 strings in
UTC (e.g. `2026-07-21T08:00:00+00:00`). Because that text format sorts in the
same order as real time, "runs in the last 24h" is a plain `WHERE started_at >= ?`
comparison — no date math in SQL needed.

## Looking at the data yourself

Your Mac ships with the `sqlite3` command-line tool:

```bash
# open the database
sqlite3 data/agent-hub.db

# then, at the sqlite> prompt:
.headers on
.mode column
SELECT * FROM task_runs ORDER BY id DESC LIMIT 10;   -- last 10 runs
SELECT status, COUNT(*) FROM task_runs GROUP BY status;   -- successes vs errors
.quit
```

Or in one line from your shell:

```bash
sqlite3 data/agent-hub.db "SELECT task_name, started_at, status FROM task_runs ORDER BY id DESC LIMIT 5;"
```

For a friendly graphical viewer, [DB Browser for SQLite](https://sqlitebrowser.org/)
is free and lets you click around the table.

## Adding your own data (optional, later)

If a task needs to remember something between runs (say, "the last id I
processed"), you can add methods to `Storage` following the same pattern:
open a connection with `with self._connect() as conn:`, run your SQL with `?`
placeholders (never paste values directly into SQL — placeholders keep you safe
from a class of bugs called SQL injection), and you're done.
