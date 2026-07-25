"""Sets up logging: messages go to BOTH the console and a rotating file.

"Rotating" means the log file is capped in size; when it fills up it's renamed
to agent-hub.log.1, agent-hub.log.2, ... and a fresh one starts. This stops the
log from growing forever on a machine that runs 24/7.
"""
from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

# One line per log record: time, level, which part logged it, and the message.
_LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"

# Rotate after ~1 MB, keeping 5 old files (~6 MB of logs at most).
_MAX_BYTES = 1_000_000
_BACKUP_COUNT = 5


def setup_logging(logs_dir: Path | str, level: str = "INFO") -> logging.Logger:
    """Configure and return the shared 'agent-hub' logger."""
    logs_dir = Path(logs_dir)
    logs_dir.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger("agent-hub")
    logger.setLevel(level.upper())

    # If this function is called twice, don't add duplicate handlers.
    if logger.handlers:
        return logger

    formatter = logging.Formatter(_LOG_FORMAT)

    # 1) Rotating file handler -> logs/agent-hub.log
    file_handler = RotatingFileHandler(
        logs_dir / "agent-hub.log",
        maxBytes=_MAX_BYTES,
        backupCount=_BACKUP_COUNT,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # 2) Console handler -> your terminal (and launchd's stdout log on the Mac).
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    return logger
