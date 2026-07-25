# 02 · Python concepts used

Every concept below is tied to a real spot in this project, so you can see it
"in the wild." Skim the ones you already know.

## Modules and packages (imports)

A **module** is just a `.py` file. A **package** is a folder of modules with an
`__init__.py` file inside it. `core/` and `tasks/` are packages.

When you see:

```python
from core.storage import Storage
```

that means "from the file `core/storage.py`, grab the `Storage` name." The dot
is a folder separator. (More on why `__init__.py` matters in the
[Glossary](10-glossary.md).)

## Classes and objects

A **class** is a blueprint; an **object** (or "instance") is a thing built from
it. `HealthCheckTask` is a class; when the app does `HealthCheckTask(ctx)` it
builds an object.

- `self` is how an object refers to itself inside its own methods.
- `__init__` is the "constructor" — it runs when the object is created.

See `core/notifier.py`: `TelegramNotifier` is a class, and
`notifier = TelegramNotifier(token, chat_id)` makes one.

## Abstract base classes (ABCs)

Look at `core/base_task.py`:

```python
class BaseTask(ABC):
    @abstractmethod
    def run(self) -> None:
        ...
```

`ABC` + `@abstractmethod` mean **"you can't use this class directly; you must
make a subclass that fills in `run()`."** It's a contract. If you write a task
and forget `run()`, Python refuses to create it — a helpful early error.

`HealthCheckTask(BaseTask)` means "HealthCheckTask **is a** BaseTask" — it
inherits everything and promises to provide `run()`.

## Class attributes vs instance attributes

In `tasks/health_check.py`:

```python
class HealthCheckTask(BaseTask):
    name = "health_check"                                  # class attribute
    schedule = {"trigger": "cron", "hour": 8, "minute": 0} # class attribute

    def run(self):
        now = datetime.now(timezone.utc)   # a local variable, just here
```

`name` and `schedule` belong to the class (same for every instance). Things set
with `self.x = ...` belong to one specific object (like `self.ctx` in
`BaseTask.__init__`).

## Dataclasses

`core/context.py` uses `@dataclass`:

```python
@dataclass
class AppContext:
    notifier: TelegramNotifier
    storage: Storage
    logger: Logger
    ...
```

A **dataclass** is a shortcut for "a class that mainly holds fields." Python
auto-writes the boring `__init__` for you. This one just bundles the shared
services together so they're easy to pass around.

## Decorators

A **decorator** is the `@something` written above a function or class. It wraps
or marks it. You've seen two: `@dataclass` (marks a class as a data holder) and
`@abstractmethod` (marks a method as "must be implemented by subclasses"). You
don't need to write your own to use this project.

## Context managers (`with`)

In `core/storage.py`:

```python
with self._connect() as conn:
    conn.execute(...)
```

`with` guarantees the database connection is properly closed afterward, even if
an error happens in the middle. You'll also see `with open(...) as f:` for
files. Rule of thumb: `with` = "use this thing, then clean it up for me."

## Type hints

Bits like `-> bool`, `name: str`, `list[type[BaseTask]]` are **type hints**.
They document what kind of value is expected/returned. Python doesn't enforce
them at runtime — they're for humans and tools — so they never change behavior.

## Exceptions and `try / except`

An **exception** is Python's way of saying "something went wrong" (e.g.
`RuntimeError`). Code can **raise** one, and other code can **catch** it:

```python
try:
    task.run()
except Exception as exc:
    # handle the problem instead of crashing
```

This is the mechanism behind crash isolation in `core/scheduler.py`. Note it
catches `Exception` (ordinary errors) but **not** `KeyboardInterrupt` — so
Ctrl+C still stops the program.

## `if __name__ == "__main__":`

At the bottom of `main.py`:

```python
if __name__ == "__main__":
    sys.exit(main())
```

This means "only run `main()` if this file was launched directly (not imported
by another file)." It's the standard way to mark a program's starting point.

---

Want to go deeper on any of these? The official
[Python tutorial](https://docs.python.org/3/tutorial/) is beginner-friendly and
free.
