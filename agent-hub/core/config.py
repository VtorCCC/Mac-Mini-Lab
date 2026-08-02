"""Loading and reading configuration.

Two sources of configuration:
  * config/.env      -> secrets (Telegram token). Loaded into environment vars.
  * settings.yaml    -> everything else (timezone, log level, task schedules).

This module finds the project folder, loads both, and offers small helper
functions the rest of the app uses.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

# The project root = the folder that CONTAINS this "core" package.
# Path(__file__) is .../agent-hub/core/config.py, so parents[1] is .../agent-hub.
BASE_DIR = Path(__file__).resolve().parents[1]

CONFIG_DIR = BASE_DIR / "config"
LOGS_DIR = BASE_DIR / "logs"
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "agent-hub.db"

ENV_PATH = CONFIG_DIR / ".env"
SETTINGS_PATH = BASE_DIR / "settings.yaml"


def load_environment() -> None:
    """Load config/.env into environment variables (if the file exists)."""
    # override=False means a real environment variable wins over the file,
    # which is handy on the Mac where launchd might already set something.
    load_dotenv(ENV_PATH, override=False)


def load_settings() -> dict[str, Any]:
    """Read settings.yaml and return it as a dict (empty dict if missing)."""
    if not SETTINGS_PATH.exists():
        return {}
    with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    # An empty YAML file parses to None; normalise that to {}.
    return data or {}


def _task_section(settings: dict[str, Any], task_name: str) -> dict[str, Any]:
    """Return the settings block for one task, or {} if none exists."""
    return (settings.get("tasks") or {}).get(task_name) or {}


def task_enabled(settings: dict[str, Any], task_name: str, default: bool) -> bool:
    """Is this task turned on? settings.yaml wins; otherwise use the default."""
    section = _task_section(settings, task_name)
    if "enabled" in section:
        return bool(section["enabled"])
    return default


def task_schedule(
    settings: dict[str, Any], task_name: str, default: dict[str, Any]
) -> dict[str, Any]:
    """The schedule dict for this task. A settings.yaml override wins if present."""
    section = _task_section(settings, task_name)
    schedule = section.get("schedule")
    if schedule:
        return dict(schedule)
    return dict(default)


def task_options(settings: dict[str, Any], task_name: str) -> dict[str, Any]:
    """The task's own `options:` block — its settings beyond enabled/schedule.

    Every task may keep arbitrary configuration here, e.g.

        tasks:
          news_digest:
            options:
              model: "gemma3:latest"

    agent-hub does not interpret the contents; the task reads what it needs.
    Returns {} when the task has no options, so callers can rely on .get().
    """
    return _task_section(settings, task_name).get("options") or {}
