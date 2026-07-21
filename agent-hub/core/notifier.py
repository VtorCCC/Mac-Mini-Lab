"""TelegramNotifier: sends messages to Telegram, and never crashes the app.

The whole point of a notifier is to tell you when something happens. It would
be ironic if the notifier itself brought the process down, so every method here
swallows its own errors and just logs them.
"""
from __future__ import annotations

import logging

import requests

logger = logging.getLogger("agent-hub.notifier")

# Telegram's Bot API endpoint template. {token} is filled in per-request.
_API_URL = "https://api.telegram.org/bot{token}/sendMessage"

# Don't let a slow network hang the whole task; give up after this many seconds.
_TIMEOUT_SECONDS = 10


class TelegramNotifier:
    """Sends text messages to a Telegram chat via the Bot API."""

    def __init__(self, token: str | None, chat_id: str | None) -> None:
        # These come from config/.env (TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID).
        self.token = token or ""
        self.chat_id = chat_id or ""

    @property
    def configured(self) -> bool:
        """True only if we have both a token and a chat id to send to."""
        return bool(self.token and self.chat_id)

    def send(self, message: str) -> bool:
        """Send a message. Returns True on success, False otherwise.

        Never raises — a failure here is logged and reported as False so the
        calling task can carry on.
        """
        if not self.configured:
            # Common on first run before you've set up a bot. Not an error.
            logger.warning(
                "Telegram not configured (missing token/chat id); "
                "skipping message: %s",
                message,
            )
            return False

        try:
            response = requests.post(
                _API_URL.format(token=self.token),
                json={"chat_id": self.chat_id, "text": message},
                timeout=_TIMEOUT_SECONDS,
            )
            response.raise_for_status()
            return True
        except Exception:
            # Log the full traceback but keep going.
            logger.exception("Failed to send Telegram message.")
            return False
