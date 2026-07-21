"""The health_check task: a daily "still alive and healthy?" report.

Runs at 8:00 every morning and sends a Telegram message with:
  * how long agent-hub has been running (uptime),
  * how much free disk space the Mac has, and
  * how many tasks ran in the last 24 hours.
"""
from __future__ import annotations

import shutil
from datetime import datetime, timezone

from core.base_task import BaseTask


def _format_duration(seconds: float) -> str:
    """Turn a number of seconds into a friendly "2d 3h 15m" style string."""
    seconds = int(seconds)
    days, seconds = divmod(seconds, 86400)
    hours, seconds = divmod(seconds, 3600)
    minutes, _ = divmod(seconds, 60)
    parts = []
    if days:
        parts.append(f"{days}d")
    if hours or days:
        parts.append(f"{hours}h")
    parts.append(f"{minutes}m")
    return " ".join(parts)


def _format_gb(num_bytes: int) -> str:
    """Turn a number of bytes into gigabytes with one decimal, e.g. "42.7 GB"."""
    return f"{num_bytes / (1024 ** 3):.1f} GB"


class HealthCheckTask(BaseTask):
    """Sends a daily uptime / disk / activity summary."""

    name = "health_check"
    # Default schedule: 8:00 AM every day. Can be overridden in settings.yaml.
    schedule = {"trigger": "cron", "hour": 8, "minute": 0}

    def run(self) -> None:
        # 1) Uptime = how long since this process started.
        now = datetime.now(timezone.utc)
        uptime_seconds = (now - self.ctx.process_start).total_seconds()
        uptime = _format_duration(uptime_seconds)

        # 2) Free disk on the root volume ("/"). shutil is part of Python — no
        #    extra library needed.
        usage = shutil.disk_usage("/")
        free = _format_gb(usage.free)
        total = _format_gb(usage.total)

        # 3) How many task runs are on record from the last 24 hours.
        runs_24h = self.ctx.storage.count_runs_last_24h()

        message = (
            "✅ agent-hub health check\n"
            f"• Uptime: {uptime}\n"
            f"• Free disk: {free} of {total}\n"
            f"• Task runs (last 24h): {runs_24h}"
        )

        # Log it (so it's in the log file too) and send it.
        self.ctx.logger.info("Health check: %s", message.replace("\n", " | "))
        self.ctx.notifier.send(message)
