"""example_task: a COPY-ME template showing the anatomy of a task.

This task is disabled by default (see settings.yaml -> example_task ->
enabled: false), so it won't run until you turn it on. It exists purely so you
have a minimal, heavily-commented example to duplicate when writing your own.

To try it: set ``enabled: true`` for example_task in settings.yaml, then run
    python main.py --run-once example_task
See study/04-adding-a-new-task.md for the full walkthrough.
"""
from __future__ import annotations

from core.base_task import BaseTask


class ExampleTask(BaseTask):
    """A do-nothing example that just writes a friendly log line."""

    # 1) A unique name. This is how settings.yaml and the database refer to it.
    name = "example_task"

    # 2) When to run. This says "every 30 minutes". Other examples:
    #       {"trigger": "cron", "hour": 9, "minute": 30}          # 9:30 every day
    #       {"trigger": "cron", "day_of_week": "mon", "hour": 7}  # Mondays at 7:00
    #       {"trigger": "interval", "hours": 6}                   # every 6 hours
    schedule = {"trigger": "interval", "minutes": 30}

    # 3) Off by default so this template doesn't actually run. settings.yaml
    #    also sets enabled: false; either place can flip it on.
    enabled = False

    def run(self) -> None:
        # Your real work goes here. You have access to shared services via
        # self.ctx — for example:
        #     self.ctx.logger.info(...)      # write to the logs
        #     self.ctx.notifier.send("hi")   # send a Telegram message
        #     self.ctx.storage...            # read/write the database
        self.ctx.logger.info("example_task ran! Replace this with real work.")
