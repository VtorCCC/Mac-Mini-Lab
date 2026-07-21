# 01 · How the project fits together

This page walks through every file and then traces exactly what happens when a
task runs.

## The two halves: `core/` and `tasks/`

- **`core/`** is the *machinery* — reusable plumbing that isn't specific to any
  one job. You'll rarely need to change it.
- **`tasks/`** is *your work* — one job per file. This is where you'll spend
  most of your time.

Keeping them separate means you can add tasks without touching the engine.

## File by file

### `main.py` — the entry point
The "front door." When you run `python main.py`, this file:
1. loads configuration,
2. sets up logging, storage, and the notifier,
3. bundles them into an **`AppContext`**,
4. discovers your tasks and starts the scheduler.

It also handles the handy flags `--list`, `--run-once`, and `--test-telegram`.

### `core/context.py` — `AppContext`
A small container object that holds the **shared services** every task needs:
the logger, notifier, storage, settings, and a few paths. Instead of passing
five things to every task, we pass one `ctx`. A task then uses
`self.ctx.notifier`, `self.ctx.storage`, etc. (More in
[02 – Python concepts](02-python-concepts-used.md#dataclasses).)

### `core/config.py` — configuration
Finds the project folder and loads two things:
- `config/.env` → secrets (your Telegram token), via `python-dotenv`.
- `settings.yaml` → timezone, log level, and per-task schedules, via `PyYAML`.

It also has helpers `task_enabled(...)` and `task_schedule(...)` that let
`settings.yaml` override what's written in a task's code.

### `core/logging_setup.py` — the logbook
Configures logging so messages go to **both** your screen **and** a rotating
file at `logs/agent-hub.log`. "Rotating" means old logs are trimmed so they
don't grow forever. (See [08 – Logging](08-logging.md).)

### `core/storage.py` — the notebook (SQLite)
A tiny wrapper around a SQLite database file (`data/agent-hub.db`). It records
each task run and can answer "how many runs in the last 24 hours?". (See
[05 – SQLite storage](05-sqlite-storage.md).)

### `core/notifier.py` — the messenger (Telegram)
Sends text messages to Telegram. Crucially, it **never throws** — if it's not
configured or the network hiccups, it just logs a warning and moves on, so it
can't take the app down.

### `core/base_task.py` — `BaseTask`
The **template** every task inherits from. It says: "every task must have a
`name`, a `schedule`, and a `run()` method." (See
[02 – Python concepts](02-python-concepts-used.md#abstract-base-classes).)

### `core/scheduler.py` — the manager
The heart of the project. It:
1. **discovers** task classes in `tasks/`,
2. **registers** each one with APScheduler using its schedule,
3. wraps every run in a **guard** (`_guarded_run`) that provides crash isolation.

### `tasks/health_check.py` — the one real task
Runs daily at 8:00 and sends uptime + free disk + 24h run count.

### `tasks/example_task.py` — a copy-me template
Disabled by default. It exists so you have a minimal, commented example to
duplicate. (See [04 – Adding a new task](04-adding-a-new-task.md).)

## The life of a task run (the important part)

Here's what happens, step by step, when 8:00 arrives:

```
   settings.yaml + task's own schedule
              │
              ▼
   scheduler.register(task)  ──►  APScheduler remembers "run this at 8:00"
                                          │
                              (8:00 arrives) │
                                          ▼
                          scheduler._guarded_run(task)
                                          │
             ┌────────────────────────────┼───────────────────────────┐
             ▼                            ▼                            ▼
        task.run()  succeeds        task.run() RAISES            (always)
             │                            │                            │
             ▼                            ▼                            ▼
     log "finished OK"        log traceback + Telegram alert   record run in
                                                                SQLite (success
                                                                or error), then
                                                                RETURN normally
```

The key: whether the task succeeds or blows up, `_guarded_run` **always**
records the outcome and **always** returns without re-raising. That's why one
failing task can never crash the process or stop the others. This is called
**crash isolation**, and you can see the exact code in
[`core/scheduler.py`](../core/scheduler.py) (`_guarded_run`).

## Why this shape?

- **Auto-discovery** means adding a task is just "add a file" — no wiring up.
- **The `AppContext` bundle** means tasks stay short and you can add new shared
  services later without rewriting every task.
- **The guard in one place** means crash isolation is guaranteed for *every*
  task automatically — you can't forget to add it.
