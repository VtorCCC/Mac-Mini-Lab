# 04 · Adding a new task (the main tutorial)

This is the skill you'll use most. We'll build a task from scratch. It takes
about 5 minutes.

## The recipe

1. Copy `tasks/example_task.py` to a new file.
2. Give the class a unique `name` and a `schedule`.
3. Write what it should do in `run()`.
4. (Optional) add it to `settings.yaml` to control it there.
5. Test it with `--run-once`.

That's it — no wiring, no registration. agent-hub **auto-discovers** any
`BaseTask` subclass in `tasks/`.

## Worked example: a "good morning" message

### Step 1 — make the file

Copy the template:

```bash
cp tasks/example_task.py tasks/good_morning.py
```

### Step 2 & 3 — edit it

Open `tasks/good_morning.py` and make it look like this:

```python
"""A friendly good-morning message every day at 7:00."""
from __future__ import annotations

from core.base_task import BaseTask


class GoodMorningTask(BaseTask):
    # 1) A unique name (no other task may use "good_morning").
    name = "good_morning"

    # 2) When to run: 7:00 every day.
    schedule = {"trigger": "cron", "hour": 7, "minute": 0}

    # 3) Turn it on (the template shipped disabled).
    enabled = True

    # 4) What it does.
    def run(self) -> None:
        self.ctx.notifier.send("☀️ Good morning! agent-hub is up and running.")
        self.ctx.logger.info("Sent the good-morning message.")
```

### Step 4 — (optional) register it in `settings.yaml`

You don't *have* to, but adding it documents it and lets you change the schedule
later without editing code:

```yaml
tasks:
  good_morning:
    enabled: true
    schedule:
      trigger: cron
      hour: 7
      minute: 0
```

### Step 5 — test it right now

```bash
python main.py --list                    # confirm "good_morning" appears
python main.py --run-once good_morning   # run it immediately
```

Once you're happy, the running scheduler (or the launchd service) will fire it
at 7:00 every day. If agent-hub is already running as a service, reload it so it
picks up the new file (see [07 – launchd](07-launchd-and-the-mac.md)).

## What you can use inside `run()`

Everything shared lives on `self.ctx`:

| You want to… | Use |
|--------------|-----|
| Send a Telegram message | `self.ctx.notifier.send("text")` |
| Write to the logs | `self.ctx.logger.info("...")` / `.warning("...")` / `.error("...")` |
| Count recent runs | `self.ctx.storage.count_runs_last_24h()` |
| Know when the app started | `self.ctx.process_start` |
| Find the project folder | `self.ctx.base_dir` |
| Read a setting | `self.ctx.settings.get("some_key")` |

You can also `import` any Python library your task needs at the top of the file
(remember to add it to `requirements.txt` and `pip install` it).

## The rules (what makes a valid task)

- It **must** subclass `BaseTask`.
- It **must** set a unique `name` (a short string).
- It **must** set a `schedule` dict (see [03 – APScheduler](03-apscheduler-and-cron.md)).
- It **must** implement `run(self)`.
- Put it in the `tasks/` folder, one class per file (conventional, not required).

## If your task hits an error, that's OK

You do **not** need `try/except` in `run()`. If your task raises an error,
agent-hub catches it, logs the full details, sends you a Telegram alert, records
it in the database, and keeps every other task running. Write your `run()` for
the happy path; let the engine handle failures. (That's crash isolation — see
[01](01-how-the-project-fits-together.md#the-life-of-a-task-run-the-important-part).)

## Turning a task off

Two ways:

- Set `enabled: false` for it in `settings.yaml` (keeps the file), or
- Delete/rename its file.

## Ideas for tasks

- Ping a website and alert you if it's down.
- Back up a folder to another disk.
- Summarize your calendar for the day.
- Delete files older than 30 days from `~/Downloads`.
- Fetch and message you the weather.
