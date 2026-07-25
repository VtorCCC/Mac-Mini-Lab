# 10 · Glossary

Plain-language definitions of terms used in this project. Skim it, or use it as
a reference when a word trips you up.

**Argument / parameter** — a value you pass into a function. In
`notifier.send("hi")`, `"hi"` is an argument.

**ABC (Abstract Base Class)** — a class you can't use directly; it defines a
contract that subclasses must fulfill. `BaseTask` is one: every task must
provide a `run()` method. See [02](02-python-concepts-used.md#abstract-base-classes).

**APScheduler** — the third-party library that runs tasks on a schedule. See
[03](03-apscheduler-and-cron.md).

**Attribute** — a piece of data attached to an object (`self.ctx`) or a class
(`name`, `schedule`).

**BlockingScheduler** — the APScheduler variety agent-hub uses. "Blocking" means
once started it takes over the process and runs forever.

**Class** — a blueprint for making objects. **Object/instance** — a thing built
from a class.

**Context (AppContext)** — our bundle of shared services (logger, notifier,
storage, settings, paths) handed to every task as `self.ctx`.

**Context manager** — the thing you use with `with`. It sets something up and
guarantees cleanup afterward (e.g. closing a file or database connection).

**Cron** — a style of schedule based on clock times ("every day at 8:00"). The
name comes from a classic Unix tool.

**Crash isolation** — agent-hub's safety net: if one task errors, it's logged
and reported but never crashes the process or stops other tasks.

**Dataclass** — a class, marked `@dataclass`, that mainly holds fields; Python
writes the boilerplate for you. `AppContext` is one.

**Decorator** — the `@name` above a function/class that modifies or marks it
(e.g. `@dataclass`, `@abstractmethod`).

**Dependency** — an external library your code needs. Ours are listed in
`requirements.txt` and installed with `pip`.

**`.env` file** — a plain text file of `KEY=value` lines holding secrets/config.
Loaded into environment variables at startup. Ours is `config/.env` (gitignored).

**Environment variable** — a named value provided by the operating system to a
program (e.g. `TELEGRAM_BOT_TOKEN`).

**Exception** — Python's signal that something went wrong. Code **raises** one;
other code can **catch** it with `try/except`.

**Handler (logging)** — a destination for log messages. We use two: a rotating
file and the console.

**Inheritance / subclass** — making a new class based on an existing one.
`HealthCheckTask(BaseTask)` is a subclass of `BaseTask` and reuses its behavior.

**ISO-8601** — a standard text format for dates/times, e.g.
`2026-07-21T08:00:00+00:00`. We store timestamps this way.

**launchd** — the macOS service manager that keeps agent-hub running 24/7. See
[07](07-launchd-and-the-mac.md).

**Log level** — how important a message is: `DEBUG < INFO < WARNING < ERROR`.

**Method** — a function that belongs to a class (e.g. `run`, `send`).

**Module** — a single `.py` file. **Package** — a folder of modules with an
`__init__.py`. `core` and `tasks` are packages.

**pip** — Python's package installer. `pip install -r requirements.txt` fetches
the project's dependencies.

**plist** — an Apple "property list" (XML) file describing a launchd job. Ours is
`com.agenthub.scheduler.plist`.

**Rotation (logs)** — capping a log file's size by starting a fresh one and
keeping a few old copies, so logs never grow without bound.

**Schedule (dict)** — the small dictionary on each task that says when it runs,
e.g. `{"trigger": "cron", "hour": 8, "minute": 0}`.

**SQLite** — a database contained in a single file, needing no server. Ours is
`data/agent-hub.db`. See [05](05-sqlite-storage.md).

**Telegram bot / token / chat id** — a Telegram account your program controls
(**bot**), authenticated by a secret **token**, sending to a specific **chat id**.
See [06](06-telegram-setup.md).

**Timezone** — the region rule that turns "8:00" into a real moment. Set in
`settings.yaml`.

**Trigger** — the *kind* of schedule: `cron` (clock times) or `interval`
(every N units).

**Type hint** — annotations like `name: str` or `-> bool` that document expected
types. Informational; they don't change how the code runs.

**venv (virtual environment)** — an isolated Python setup for one project, in the
`.venv/` folder, so this project's dependencies don't clash with others.

**YAML** — a human-friendly config file format. `settings.yaml` uses it.
