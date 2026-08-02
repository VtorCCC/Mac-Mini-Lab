# CLAUDE.md

Guidance for Claude Code when working in the **Mac-Mini-Lab** repo.

---

## 1. What this repo is

A personal lab for things that run on a **Mac mini** kept on 24/7 at home, plus
the notes made while learning to build them. It is a *collection of small,
independent projects*, not one application — each top-level folder is its own
self-contained component with its own README, dependencies, and tests.

The repo doubles as a study space: several components carry a `study/` folder of
beginner-friendly guides. **Treat those guides as part of the deliverable** — if
a change makes a guide wrong, fix the guide in the same change.

## 2. Layout

```
Mac-Mini-Lab/
├── CLAUDE.md      <- you are here: how to work in this repo
├── STATUS.md      <- living snapshot: what works, what's in flight, what's next
├── WORKLOG.md     <- dated, append-only record of work sessions
├── README.md      <- the repo's public front door
└── agent-hub/     <- component: always-on scheduled-task host (APScheduler + launchd)
```

New components get their own top-level folder and a row in `STATUS.md`.

### Component: `agent-hub/`

One always-on Python process that hosts many scheduled tasks. Read
[`agent-hub/README.md`](agent-hub/README.md) first; the deep detail lives in
[`agent-hub/study/`](agent-hub/study/).

| Path | Role |
|------|------|
| `main.py` | Entry point + CLI (`--list`, `--run-once`, `--test-telegram`) |
| `core/scheduler.py` | Task auto-discovery, registration, **crash isolation** |
| `core/base_task.py` | `BaseTask` ABC — every task subclasses it |
| `core/config.py` | Loads `config/.env` (secrets) + `settings.yaml` (behavior) |
| `core/context.py` | `AppContext` — the shared-services bundle tasks receive |
| `core/storage.py` | SQLite record of every task run |
| `core/notifier.py` | Telegram alerts; designed never to crash the app |
| `tasks/` | One task class per file, auto-discovered |
| `settings.yaml` | Timezone, log level, per-task `enabled` + `schedule` |

Load-bearing invariants — do not break these without saying so explicitly:

- **Crash isolation.** `AgentScheduler._guarded_run` catches every exception so
  one failing task can never stop the process or the other tasks.
- **Auto-discovery.** Dropping a file in `tasks/` is enough; nothing registers
  tasks by hand.
- **Config over code.** Schedules and on/off switches belong in `settings.yaml`,
  not in Python. A task's class attributes are only the *default*.
- **APScheduler is pinned to 3.x.** 4.x is a different API; don't "upgrade" it.
- **Notifier failures are non-fatal.** Telegram being down must never break a run.

## 3. Environment reality

- **Development happens on Windows** (this machine), in PowerShell or Git Bash.
- **The deployment target is macOS** (the Mac mini). Anything `launchd`-related
  — `com.agenthub.scheduler.plist`, `launchctl` — **cannot be tested here.**
  Write it carefully, say plainly that it's unverified, and leave verification
  to the user on the Mac.
- Python 3.11+ (the code uses `X | None` type hints and modern stdlib).
- Paths differ between the two machines. Don't hardcode either one — use
  `pathlib` relative to `BASE_DIR`, as `core/config.py` already does.

## 4. Commands

Run from inside the component folder (`agent-hub/`):

```bash
python -m venv .venv
```

```bash
pip install -r requirements-dev.txt
```

```bash
python main.py --list
```

```bash
python main.py --run-once health_check
```

```bash
python -m pytest
```

`--run-once` goes through the same guard as a scheduled run (logging, alerting,
DB recording), so it is the honest way to test a task.

## 5. Conventions to match

The existing code has a deliberate, consistent voice. Match it:

- `from __future__ import annotations` at the top of every module.
- A module-level docstring saying *what this file is for*, in plain language.
- Type hints on public functions; PEP 604 unions (`str | None`).
- **Comments explain "why", not "what."** The existing comments teach a reader
  who is still learning Python — keep that register. Don't strip them.
- Stdlib first; a new third-party dependency needs a one-line justification
  comment in `requirements.txt`, like the existing entries have.
- Secrets live in `config/.env` only, which is gitignored. **Never** commit a
  token, chat id, or anything from `.env`. Update `.env.example` instead.
- Generated state (`logs/*.log`, `data/*.db`) stays gitignored.

## 6. Working agreement

- Read the component's `README.md` and relevant `study/` guide before changing it.
- Prefer small, reviewable changes over sweeping refactors.
- If a change touches behavior a `study/` guide describes, update that guide.
- Tests: the suite protects the 24-hour run count, auto-discovery, and crash
  isolation. If you change any of those three, the tests must change with them
  — and you must say why.
- Report honestly: if something is untested (especially macOS-only paths), say
  so rather than implying it's verified.

## 7. Logging protocol — **do this, it's the point of this repo**

Two files track state. Keep both current.

**`STATUS.md`** — the *now*. Overwrite in place; it always describes the present.
Update it whenever a component's state changes: something starts working, breaks,
gets deployed to the Mac, or moves on/off the next-up list.

**`WORKLOG.md`** — the *history*. Append a new entry at the top (newest first) at
the end of any session that changed files or produced a decision worth
remembering. Never edit past entries; if something turned out wrong, say so in a
new entry.

At the end of a working session:

1. Append a `WORKLOG.md` entry using the template at the top of that file.
2. Reconcile `STATUS.md` with what is now true.
3. Include both files in the same commit as the work they describe.

Skip the worklog only for pure no-op sessions (questions answered, nothing
changed). When in doubt, log it — a thin entry beats a missing one.

## 8. Git

- Branch off `main`: `docs/...`, `feat/...`, `fix/...`, `chore/...`.
- Commit messages: imperative subject line, ~72 chars, body explaining *why*.
- Don't commit or push unless asked. When asked while on `main`, branch first.
- `gh` is **not installed** on this machine — open pull requests via the GitHub
  web UI (give the user the compare link) rather than trying to shell out.
