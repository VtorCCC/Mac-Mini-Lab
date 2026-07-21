"""BaseTask: the template every scheduled job inherits from.

To create a new job you subclass BaseTask, give it a ``name`` and a ``schedule``,
and fill in ``run()``. See study/04-adding-a-new-task.md for a walkthrough.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    # Imported only for type hints to avoid an import cycle at runtime.
    from core.context import AppContext


class BaseTask(ABC):
    """Abstract base class for all tasks.

    "Abstract" means you never use BaseTask directly — you create subclasses of
    it. Each subclass MUST set two class attributes and implement one method:

        name:     A short, unique identifier, e.g. "health_check". This is how
                  the task is referenced in settings.yaml and in the database.

        schedule: A dict describing WHEN to run, passed straight to APScheduler.
                  Examples:
                      {"trigger": "cron", "hour": 8, "minute": 0}   # 8:00 daily
                      {"trigger": "interval", "minutes": 15}        # every 15 min
                  See study/03-apscheduler-and-cron.md.

        run():    The work to perform. Raise an exception if something goes
                  wrong — the scheduler catches it, logs it, alerts you, and
                  keeps every OTHER task running (see core/scheduler.py).
    """

    # Subclasses override these. The defaults here are deliberately "empty" so a
    # forgotten override fails loudly and early (see the checks in __init__).
    name: str = ""
    schedule: dict[str, Any] = {}

    # Whether the task runs by default. settings.yaml can override this.
    enabled: bool = True

    def __init__(self, ctx: "AppContext") -> None:
        # Guard against subclasses that forgot the required pieces.
        if not self.name:
            raise ValueError(
                f"{type(self).__name__} must set a class attribute `name`."
            )
        if not self.schedule:
            raise ValueError(
                f"Task '{self.name}' must set a class attribute `schedule`."
            )
        # Every task gets the shared services bundle. Reach for what you need
        # via self.ctx, e.g. self.ctx.logger / self.ctx.notifier / self.ctx.storage.
        self.ctx = ctx

    @abstractmethod
    def run(self) -> None:
        """Do the task's work. Implemented by every subclass."""
        raise NotImplementedError
