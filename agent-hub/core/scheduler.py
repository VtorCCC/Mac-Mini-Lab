"""AgentScheduler: finds tasks, schedules them, and keeps them isolated.

This is the heart of agent-hub. It:
  1. Auto-discovers task classes in the tasks/ package.
  2. Registers each enabled task with APScheduler.
  3. Wraps every run in a guard so that if one task raises an exception, it is
     logged and pushed to Telegram, but NEVER takes down the process or the
     other tasks ("crash isolation").
"""
from __future__ import annotations

import importlib
import inspect
import pkgutil
from datetime import datetime, timezone
from typing import Any

from apscheduler.events import EVENT_JOB_ERROR
from apscheduler.schedulers.blocking import BlockingScheduler

from core import config as config_module
from core.base_task import BaseTask
from core.context import AppContext


def discover_task_classes(package_name: str = "tasks") -> list[type[BaseTask]]:
    """Find every concrete BaseTask subclass inside the given package.

    This is what makes tasks "auto-discovered": drop a new file in tasks/ that
    defines a BaseTask subclass, and it's picked up automatically — no need to
    register it anywhere by hand.
    """
    found: list[type[BaseTask]] = []
    package = importlib.import_module(package_name)

    # Walk each module (file) inside the tasks/ package.
    for module_info in pkgutil.iter_modules(package.__path__):
        module = importlib.import_module(f"{package_name}.{module_info.name}")

        # Look at every class defined in that module.
        for _, obj in inspect.getmembers(module, inspect.isclass):
            is_task = issubclass(obj, BaseTask)
            # Skip BaseTask itself, and skip classes merely imported into the
            # module (we only want ones actually defined there).
            defined_here = obj.__module__ == module.__name__
            if is_task and obj is not BaseTask and defined_here:
                found.append(obj)

    return found


class AgentScheduler:
    """Wraps APScheduler's BlockingScheduler with discovery + crash isolation."""

    def __init__(self, ctx: AppContext) -> None:
        self.ctx = ctx

        # The timezone comes from settings.yaml. If it's blank, APScheduler
        # falls back to the machine's local timezone.
        timezone_name = ctx.settings.get("timezone")
        if timezone_name:
            self.scheduler = BlockingScheduler(timezone=timezone_name)
        else:
            self.scheduler = BlockingScheduler()

        # Backstop: if an exception ever slips past our guard, still log it.
        self.scheduler.add_listener(self._on_job_error, EVENT_JOB_ERROR)

    def register(self, task: BaseTask) -> None:
        """Add one task to the scheduler using its (possibly overridden) schedule."""
        schedule = config_module.task_schedule(
            self.ctx.settings, task.name, task.schedule
        )
        self.ctx.logger.info(
            "Registering task '%s' with schedule %s", task.name, schedule
        )
        # `schedule` is a dict like {"trigger": "cron", "hour": 8, "minute": 0}.
        # Passing it as **schedule hands the trigger + its options to APScheduler.
        self.scheduler.add_job(
            self._guarded_run,
            args=[task],
            id=task.name,
            name=task.name,
            replace_existing=True,
            max_instances=1,          # never run two copies of the same task at once
            misfire_grace_time=300,   # still run if we're up to 5 minutes late
            **schedule,
        )

    def run_once(self, task: BaseTask) -> None:
        """Run a single task immediately, through the same safety guard.

        Used by ``python main.py --run-once <name>`` for testing, so a manual
        run behaves exactly like a scheduled one (logging, alerting, recording).
        """
        self._guarded_run(task)

    def _guarded_run(self, task: BaseTask) -> None:
        """Run one task safely and record the outcome.

        This is the crash-isolation guard. No matter what ``task.run()`` does,
        this method:
          * records the run (success or error) in SQLite, and
          * on error, logs the traceback and sends a Telegram alert,
        and it NEVER re-raises, so the scheduler and all other tasks keep going.
        """
        started_at = datetime.now(timezone.utc)
        status = "success"
        error_message: str | None = None

        try:
            self.ctx.logger.info("Running task '%s'...", task.name)
            task.run()
            self.ctx.logger.info("Task '%s' finished OK.", task.name)
        except Exception as exc:  # we INTENTIONALLY catch everything here
            status = "error"
            error_message = f"{type(exc).__name__}: {exc}"
            # Full traceback to the logs...
            self.ctx.logger.exception("Task '%s' raised an exception.", task.name)
            # ...and a short alert to Telegram.
            self.ctx.notifier.send(
                f"⚠️ agent-hub: task '{task.name}' failed.\n{error_message}"
            )
        finally:
            finished_at = datetime.now(timezone.utc)
            # Recording must not crash the guard either, so guard it too.
            try:
                self.ctx.storage.record_run(
                    task.name, started_at, finished_at, status, error_message
                )
            except Exception:
                self.ctx.logger.exception(
                    "Failed to record run for task '%s'.", task.name
                )

    def _on_job_error(self, event: Any) -> None:
        """APScheduler-level backstop; normally never fires thanks to the guard."""
        self.ctx.logger.error(
            "APScheduler reported an error in job '%s'.", event.job_id
        )

    def start(self) -> None:
        """Start the blocking scheduler loop (runs until interrupted)."""
        self.ctx.logger.info("Scheduler starting. Press Ctrl+C to stop.")
        self.scheduler.start()

    def shutdown(self) -> None:
        """Stop the scheduler cleanly."""
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)
