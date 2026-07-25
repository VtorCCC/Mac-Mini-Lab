"""agent-hub entry point.

Run me directly to start the scheduler:
    python main.py

Handy one-off commands:
    python main.py --list                    # show discovered tasks + schedules
    python main.py --run-once health_check   # run one task right now
    python main.py --test-telegram           # send a test Telegram message

See README.md and the study/ folder for details.
"""
from __future__ import annotations

import argparse
import os
import signal
import sys
from datetime import datetime, timezone

from core import config as config_module
from core.context import AppContext
from core.logging_setup import setup_logging
from core.notifier import TelegramNotifier
from core.scheduler import AgentScheduler, discover_task_classes
from core.storage import Storage


def build_context() -> AppContext:
    """Load configuration and assemble the shared AppContext."""
    # 1) Load secrets from config/.env and settings from settings.yaml.
    config_module.load_environment()
    settings = config_module.load_settings()

    # 2) Set up logging first so everything after this is logged.
    log_level = settings.get("log_level", "INFO")
    logger = setup_logging(config_module.LOGS_DIR, level=log_level)

    # 3) Prepare storage (creates data/agent-hub.db and its table if needed).
    storage = Storage(config_module.DB_PATH)
    storage.init_db()

    # 4) Prepare the Telegram notifier from environment variables.
    notifier = TelegramNotifier(
        token=os.getenv("TELEGRAM_BOT_TOKEN"),
        chat_id=os.getenv("TELEGRAM_CHAT_ID"),
    )

    # 5) Bundle everything a task might need into one context object.
    return AppContext(
        notifier=notifier,
        storage=storage,
        logger=logger,
        settings=settings,
        process_start=datetime.now(timezone.utc),
        base_dir=config_module.BASE_DIR,
        db_path=config_module.DB_PATH,
    )


def load_tasks(ctx: AppContext, only_enabled: bool = True) -> list:
    """Discover task classes and instantiate them.

    When only_enabled is True, tasks turned off in settings.yaml are skipped.
    """
    tasks = []
    for task_cls in discover_task_classes():
        task = task_cls(ctx)
        enabled = config_module.task_enabled(ctx.settings, task.name, task.enabled)
        if only_enabled and not enabled:
            ctx.logger.info("Skipping disabled task '%s'.", task.name)
            continue
        tasks.append(task)
    return tasks


def cmd_list(ctx: AppContext) -> int:
    """Print every discovered task, whether it's enabled, and its schedule."""
    print("Discovered tasks:\n")
    for task_cls in discover_task_classes():
        task = task_cls(ctx)
        enabled = config_module.task_enabled(ctx.settings, task.name, task.enabled)
        schedule = config_module.task_schedule(ctx.settings, task.name, task.schedule)
        state = "enabled " if enabled else "disabled"
        print(f"  [{state}] {task.name:<16} schedule={schedule}")
    print()
    return 0


def cmd_run_once(ctx: AppContext, task_name: str) -> int:
    """Run a single task immediately (ignores enabled/disabled)."""
    scheduler = AgentScheduler(ctx)
    for task_cls in discover_task_classes():
        task = task_cls(ctx)
        if task.name == task_name:
            scheduler.run_once(task)
            return 0
    print(f"No task named '{task_name}'. Try: python main.py --list")
    return 1


def cmd_test_telegram(ctx: AppContext) -> int:
    """Send a test message to confirm your Telegram setup works."""
    ok = ctx.notifier.send("👋 Hello from agent-hub! Your Telegram setup works.")
    if ok:
        print("Sent! Check your Telegram chat.")
        return 0
    print(
        "Could not send. Check TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in "
        "config/.env (see study/06-telegram-setup.md)."
    )
    return 1


def run_scheduler(ctx: AppContext) -> int:
    """Register all enabled tasks and start the (blocking) scheduler."""
    scheduler = AgentScheduler(ctx)

    tasks = load_tasks(ctx, only_enabled=True)
    if not tasks:
        ctx.logger.warning("No enabled tasks found. The scheduler has nothing to do.")
    for task in tasks:
        scheduler.register(task)

    # Make Ctrl+C / `launchctl unload` shut things down cleanly.
    def _handle_stop(signum, _frame):
        ctx.logger.info("Received signal %s; shutting down.", signum)
        scheduler.shutdown()

    signal.signal(signal.SIGINT, _handle_stop)
    signal.signal(signal.SIGTERM, _handle_stop)

    ctx.logger.info("agent-hub started with %d task(s).", len(tasks))
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="agent-hub scheduled task host.")
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--list", action="store_true", help="List discovered tasks and exit."
    )
    group.add_argument(
        "--run-once", metavar="TASK", help="Run one task now and exit."
    )
    group.add_argument(
        "--test-telegram",
        action="store_true",
        help="Send a test Telegram message and exit.",
    )
    args = parser.parse_args(argv)

    ctx = build_context()

    if args.list:
        return cmd_list(ctx)
    if args.run_once:
        return cmd_run_once(ctx, args.run_once)
    if args.test_telegram:
        return cmd_test_telegram(ctx)

    return run_scheduler(ctx)


if __name__ == "__main__":
    sys.exit(main())
