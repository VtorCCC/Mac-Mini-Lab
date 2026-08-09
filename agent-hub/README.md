# agent-hub

A single, always-on Python process that hosts multiple **scheduled tasks** on a
Mac mini. One process wakes up, runs your jobs on their schedules, records what
happened, and messages you on Telegram if something breaks — all kept alive by
macOS's built-in `launchd`.

It ships with two real tasks:

- **`health_check`** — every morning at 8:00, sends you uptime, free disk space,
  and how many tasks ran in the last 24 hours.
- **`news_digest`** — every morning at 7:00, fetches RSS across four categories,
  summarizes it with a local LLM ([Ollama](https://ollama.com/)), writes
  `data/news/YYYY-MM-DD.md`, and Telegrams you the highlights. Full walkthrough:
  [`study/11-the-news-digest-task.md`](study/11-the-news-digest-task.md).

> **New to coding?** Head to the [`study/`](study/) folder. It's a friendly,
> guided tour of this exact project so you can confidently edit and maintain it.
> Start with [`study/00-start-here.md`](study/00-start-here.md).

---

## What it does

- **Hosts many tasks in one process** using [APScheduler](https://apscheduler.readthedocs.io/).
- **Auto-discovers tasks** — drop a file in `tasks/` and it's picked up automatically.
- **Crash isolation** — if one task throws an error, it's logged and pushed to
  Telegram, but it never crashes the process or stops the other tasks.
- **Records every run** in a small SQLite database.
- **Rotating logs** in `logs/` so the log files never grow forever.
- **Runs 24/7** via a `launchd` job with `KeepAlive` (auto-restarts on crash/reboot).

## Requirements

- macOS (a Mac mini is the intended home) — for local development any OS with
  Python works; only the `launchd` part is macOS-specific.
- Python 3.11+
- A Telegram bot (optional — the app runs fine without one, it just won't send
  messages; see [`study/06-telegram-setup.md`](study/06-telegram-setup.md)).
- [Ollama](https://ollama.com/) with a model pulled — only for the `news_digest`
  task. Without it that task degrades to headlines without summaries; disable it
  in `settings.yaml` if you don't want it at all.

---

## Quick start

```bash
# 1. Get the code onto your Mac and enter the folder
cd agent-hub

# 2. Create an isolated Python environment ("virtualenv") and activate it
python3 -m venv .venv
source .venv/bin/activate

# 3. Install the dependencies
pip install -r requirements.txt

# 4. Set up your secrets (Telegram). Copy the example, then edit it.
cp config/.env.example config/.env
#   ...open config/.env in a text editor and fill in the two values.

# 5. See what tasks exist
python main.py --list

# 6. Try the health check right now (don't wait until 8:00)
python main.py --run-once health_check
```

If you haven't set up Telegram yet, step 6 still works — it just logs a
"Telegram not configured" warning instead of sending a message.

---

## Configuration

There are **two** places to configure things, and you never need to touch the
Python code to change them:

### 1. `config/.env` — your secrets

Copied from `config/.env.example`. Holds your Telegram bot token and chat id.
This file is **gitignored** so your secrets never end up on GitHub.

```ini
TELEGRAM_BOT_TOKEN=123456789:AAE...your-token...
TELEGRAM_CHAT_ID=987654321
```

See [`study/06-telegram-setup.md`](study/06-telegram-setup.md) for how to get these.

### 2. `settings.yaml` — behavior & schedules

Change the timezone, the log level, and **when each task runs** — or turn a task
on/off — without editing code:

```yaml
timezone: "America/New_York"   # set this to your Mac's timezone
log_level: "INFO"

tasks:
  health_check:
    enabled: true
    schedule:
      trigger: cron
      hour: 8
      minute: 0
```

Anything you leave out falls back to the default defined in the task's code.
See [`study/03-apscheduler-and-cron.md`](study/03-apscheduler-and-cron.md) for
all the schedule options.

---

## Running it manually

```bash
python main.py                     # start the scheduler (runs forever; Ctrl+C to stop)
python main.py --list              # list discovered tasks + their schedules, then exit
python main.py --run-once health_check   # run one task immediately, then exit
python main.py --test-telegram     # send a test Telegram message, then exit
```

`--run-once` and `--test-telegram` are your best friends for testing changes.

---

## Running 24/7 with launchd

`launchd` is the macOS service manager. The included
`com.agenthub.scheduler.plist` tells it to keep `agent-hub` running forever and
restart it if it ever crashes or the Mac reboots.

**1. Edit the plist paths.** Open `com.agenthub.scheduler.plist` and replace
every `YOUR_USERNAME` (and the folder path, if you didn't put it at
`/Users/YOUR_USERNAME/agent-hub`). It references the venv's Python at
`.venv/bin/python3`, so make sure you created the venv (Quick start step 2).

**2. Copy it into your LaunchAgents folder.**

```bash
cp com.agenthub.scheduler.plist ~/Library/LaunchAgents/
```

**3. Load it (this also starts it, because `RunAtLoad` is true).**

```bash
launchctl load ~/Library/LaunchAgents/com.agenthub.scheduler.plist
```

**4. Check it's running.**

```bash
launchctl list | grep agenthub
#   A line with a PID (a number) in the first column means it's running.
```

**5. Watch the logs.**

```bash
tail -f logs/agent-hub.log        # the app's own log
tail -f logs/launchd.err.log      # anything launchd captured on startup errors
```

**To stop / reload after changes:**

```bash
launchctl unload ~/Library/LaunchAgents/com.agenthub.scheduler.plist   # stop
launchctl load   ~/Library/LaunchAgents/com.agenthub.scheduler.plist   # start again
```

A fuller walkthrough (with troubleshooting) is in
[`study/07-launchd-and-the-mac.md`](study/07-launchd-and-the-mac.md).

---

## Project structure

```
agent-hub/
├── main.py                 # entry point (--list / --run-once / --test-telegram)
├── settings.yaml           # timezone, log level, per-task schedules (no code needed)
├── requirements.txt        # dependencies
├── com.agenthub.scheduler.plist   # the launchd service definition
├── config/.env.example     # template for your secrets -> copy to config/.env
├── core/                   # the reusable machinery (not specific to any one task)
│   ├── base_task.py        # BaseTask: the template every task inherits from
│   ├── scheduler.py        # discovery + scheduling + crash isolation
│   ├── notifier.py         # Telegram messages (never crashes the app)
│   ├── storage.py          # SQLite: records task runs
│   ├── logging_setup.py    # rotating file + console logging
│   ├── config.py           # loads .env + settings.yaml
│   └── context.py          # AppContext: the shared-services bundle tasks receive
├── tasks/                  # your jobs live here, one class per file (auto-discovered)
│   ├── health_check.py     # the daily health report (required task)
│   ├── news_digest.py      # the morning news briefing (thin: calls services/news)
│   └── example_task.py     # a disabled, copy-me template
├── services/               # libraries too big for a single task file
│   └── news/               # RSS fetch, LLM summarization, markdown output
├── tests/                  # a small pytest suite
├── logs/                   # rotating logs land here (gitignored)
├── data/                   # the SQLite database lands here (gitignored)
│   └── news/               # generated daily digests (gitignored)
└── study/                  # << beginner-friendly guides to this project >>
```

---

## Running the tests

```bash
pip install -r requirements-dev.txt   # installs pytest
python -m pytest
```

The tests check the three things most worth protecting: the 24-hour run count,
task auto-discovery, and crash isolation.

---

## The study space

The [`study/`](study/) folder is a mini-course built around *this* codebase:

| Guide | What it covers |
|-------|----------------|
| [00 – Start here](study/00-start-here.md) | The 5-minute tour |
| [01 – How the project fits together](study/01-how-the-project-fits-together.md) | File-by-file + the life of a task run |
| [02 – Python concepts used](study/02-python-concepts-used.md) | Classes, ABCs, imports, dataclasses… tied to real lines |
| [03 – APScheduler & cron](study/03-apscheduler-and-cron.md) | Triggers, cron vs interval, timezones |
| [04 – Adding a new task](study/04-adding-a-new-task.md) | The main "how to maintain it" tutorial |
| [05 – SQLite storage](study/05-sqlite-storage.md) | What's stored and how to inspect it |
| [06 – Telegram setup](study/06-telegram-setup.md) | Get a bot token + chat id |
| [07 – launchd & the Mac](study/07-launchd-and-the-mac.md) | Keeping it alive 24/7 |
| [08 – Logging](study/08-logging.md) | Where logs go, rotation, log levels |
| [09 – Troubleshooting / FAQ](study/09-troubleshooting-faq.md) | Common problems + fixes |
| [10 – Glossary](study/10-glossary.md) | Plain-language definitions |
| [11 – The news digest task](study/11-the-news-digest-task.md) | A real task end-to-end: RSS, a local LLM, and the traps |
| [12 – Reporting a bug on GitHub](study/12-reporting-a-bug-on-github.md) | Turning "it's broken" into an issue someone can act on |
