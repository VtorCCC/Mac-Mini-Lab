"""Test that a failing task is isolated: recorded as an error, never re-raised.

This is the most important guarantee in agent-hub — one broken task must not
take down the whole process or stop the other tasks.
"""
from datetime import datetime, timezone
from pathlib import Path

from core.base_task import BaseTask
from core.context import AppContext
from core.logging_setup import setup_logging
from core.notifier import TelegramNotifier
from core.scheduler import AgentScheduler
from core.storage import Storage


class _BoomTask(BaseTask):
    """A task that always fails on purpose."""

    name = "boom"
    schedule = {"trigger": "interval", "minutes": 1}

    def run(self):
        raise RuntimeError("intentional failure")


def _make_ctx(tmp_path: Path) -> AppContext:
    storage = Storage(tmp_path / "test.db")
    storage.init_db()
    return AppContext(
        notifier=TelegramNotifier(token=None, chat_id=None),  # no-op notifier
        storage=storage,
        logger=setup_logging(tmp_path / "logs", "INFO"),
        settings={},
        process_start=datetime.now(timezone.utc),
        base_dir=tmp_path,
        db_path=tmp_path / "test.db",
    )


def test_failing_task_is_isolated(tmp_path):
    ctx = _make_ctx(tmp_path)
    scheduler = AgentScheduler(ctx)

    # This must NOT raise, even though the task does.
    scheduler.run_once(_BoomTask(ctx))

    # And the failure must still be recorded (so it counts as a run).
    assert ctx.storage.count_runs_last_24h() == 1
