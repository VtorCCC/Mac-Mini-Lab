# 09 · Troubleshooting / FAQ

A grab-bag of "it's not working" situations and how to fix them. When in doubt,
**read `logs/agent-hub.log`** first — it usually says exactly what went wrong.

## Setup & running

**`ModuleNotFoundError: No module named 'apscheduler'` (or yaml, dotenv, requests)**
The dependencies aren't installed in the environment you're using. Activate the
virtualenv and install:

```bash
source .venv/bin/activate
pip install -r requirements.txt
```

**`python: command not found` / it uses the wrong Python**
Use `python3` explicitly, and make sure the venv is activated (your prompt
should show `(.venv)`). Recreate it if needed:
`python3 -m venv .venv && source .venv/bin/activate`.

**`python main.py --list` shows no tasks**
Every task file in `tasks/` must define a class that subclasses `BaseTask` with a
`name` and `schedule`. Check for a typo or a Python error in the file (run
`python -c "import tasks.your_file"` to see the error).

**My new task doesn't appear**
It must be a `BaseTask` subclass *defined in* a file inside `tasks/`. Confirm the
class has `name`, `schedule`, and `run()`. Then `python main.py --list` again.

## Scheduling

**My task didn't run at the time I expected**
Almost always a **timezone** issue. `cron` times use the `timezone` in
`settings.yaml`. Set it to your Mac's timezone (e.g. `America/New_York`). See
[03 – APScheduler & cron](03-apscheduler-and-cron.md#timezones-important).

**I changed `settings.yaml` but nothing changed**
Settings are read at startup. Restart: stop the process (Ctrl+C) and start it
again, or unload/load the launchd job.

**Task didn't run because the Mac was asleep**
A sleeping Mac can't run jobs. If it wakes within 5 minutes of the scheduled
time the run still happens (`misfire_grace_time`); later than that it's skipped
until next time. For always-on reliability, set the Mac to not sleep (System
Settings → Displays/Battery → prevent sleeping), which is typical for a Mac mini
acting as a little server.

## Telegram

**"Telegram not configured" in the logs**
`config/.env` is missing or a value is blank. See
[06 – Telegram setup](06-telegram-setup.md). (This is only a warning — the app
still runs.)

**`--test-telegram` fails to send**
Check the token is exact, and that you sent your bot a message first so it can
find your chat id. Re-run [06 – Telegram setup](06-telegram-setup.md) step 2.

## launchd (the 24/7 service)

**It won't start / keeps restarting**
Read `logs/launchd.err.log`. The usual cause is a wrong path in the plist —
replace `YOUR_USERNAME` and make sure `.venv/bin/python3` exists. See
[07 – launchd & the Mac](07-launchd-and-the-mac.md#common-gotchas).

**How do I know it's actually running?**
`launchctl list | grep agenthub` — a PID (number) on the left means yes. The
other number is the last exit code (`0` = clean).

## Database & logs

**Where's the run history?**
`data/agent-hub.db`. Inspect it with
`sqlite3 data/agent-hub.db "SELECT * FROM task_runs ORDER BY id DESC LIMIT 10;"`.
See [05 – SQLite storage](05-sqlite-storage.md).

**Can I delete the logs / database?**
Yes. Both are regenerated automatically. Deleting `data/agent-hub.db` resets the
run history (and the 24h count starts from zero again).

## General debugging tips

- Turn up detail: set `log_level: "DEBUG"` in `settings.yaml`, reproduce, then
  set it back.
- Test one thing at a time with `python main.py --run-once <task>`.
- Read the traceback bottom-up: the last line names the error; the lines above
  show where it happened.
- Still stuck? The error message pasted into a search engine (or asked to an AI
  assistant) usually gets you far.
