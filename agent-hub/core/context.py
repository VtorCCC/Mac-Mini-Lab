"""The AppContext: one bag of shared services every task receives.

Rather than passing the logger, notifier, storage, etc. around individually,
we bundle them into a single object and hand that to each task. A task then
reaches for whatever it needs, e.g. ``self.ctx.notifier.send("hi")``.

This keeps task code short and means we can add new shared services later
without changing every task's constructor.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from logging import Logger
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    # Imported only for type hints. Doing this under TYPE_CHECKING avoids an
    # import cycle at runtime (notifier/storage never import this module, but
    # this keeps things tidy and fast to import).
    from core.notifier import TelegramNotifier
    from core.storage import Storage


@dataclass
class AppContext:
    """Shared services handed to every task.

    Attributes:
        notifier:      Sends Telegram messages (never raises).
        storage:       SQLite helper that records task runs.
        logger:        The shared logger; writes to console + logs/agent-hub.log.
        settings:      The parsed contents of settings.yaml (a plain dict).
        process_start: When this agent-hub process started (UTC). Used to
                       compute "uptime".
        base_dir:      The agent-hub project folder on disk.
        db_path:       Full path to the SQLite database file.
    """

    notifier: "TelegramNotifier"
    storage: "Storage"
    logger: Logger
    settings: dict[str, Any]
    process_start: datetime
    base_dir: Path
    db_path: Path
