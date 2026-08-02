"""What the news digest fetches, and the knobs that control it.

The values below are *defaults*. Following agent-hub's "config over code" rule,
every one of them can be overridden in ``settings.yaml`` under:

    tasks:
      news_digest:
        options:
          model: "gemma3:latest"
          lookback_hours: 24

so changing the model or the feed list never needs a Python edit.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# -----------------------------------------------------------------------------
# Feeds, grouped into the categories that become sections of the digest.
# These must be real RSS/Atom URLs — a normal web page won't parse.
# -----------------------------------------------------------------------------
DEFAULT_FEEDS: dict[str, list[str]] = {
    "Technology & AI": [
        "https://hnrss.org/frontpage",
        "https://feeds.arstechnica.com/arstechnica/index",
        "https://www.theverge.com/rss/index.xml",
        "https://techcrunch.com/feed/",
    ],
    "World": [
        "https://feeds.bbci.co.uk/news/world/rss.xml",
        "https://www.aljazeera.com/xml/rss/all.xml",
        "https://www.theguardian.com/world/rss",
    ],
    "Finance": [
        "https://feeds.content.dowjones.io/public/rss/RSSMarketsMain",
        "https://www.ft.com/rss/home",
        "https://www.economist.com/finance-and-economics/rss.xml",
    ],
    "Science": [
        "https://www.nature.com/nature.rss",
        "https://www.quantamagazine.org/feed/",
        "https://www.sciencedaily.com/rss/all.xml",
    ],
}

# Ollama's OpenAI-compatible endpoint. The health check derives the /api/tags
# URL from this, so you only ever configure one address.
DEFAULT_BASE_URL = "http://localhost:11434/v1"

# Override in settings.yaml to match whatever `ollama list` shows on the Mac
# mini. The original project defaulted to "gemma4:latest"; that model crashes
# llama-server on the Windows dev machine (see study/11), so the default here
# is one that was actually verified to work.
DEFAULT_MODEL = "gemma3:latest"

# How the model is asked to return structured JSON. Defined here rather than in
# summarizer.py so this module stays importable without pydantic-ai installed.
# The measured trade-offs are in the table in services/news/summarizer.py.
OUTPUT_MODES = ("native", "tool", "prompted")
DEFAULT_OUTPUT_MODE = "native"


@dataclass(frozen=True)
class NewsConfig:
    """Everything the digest run needs to know, resolved from settings.yaml."""

    feeds: dict[str, list[str]] = field(default_factory=lambda: dict(DEFAULT_FEEDS))
    model: str = DEFAULT_MODEL
    base_url: str = DEFAULT_BASE_URL

    # How the model is asked to return structured JSON: "native", "tool", or
    # "prompted". See the table in services/news/summarizer.py — "native" is
    # the one most local models can actually honour.
    output_mode: str = DEFAULT_OUTPUT_MODE

    # Only include items published within this many hours of the run.
    lookback_hours: int = 24
    # Caps that keep the LLM prompt (and the run time) bounded.
    item_cap_per_feed: int = 5
    category_total_cap: int = 15
    desc_truncate_chars: int = 800

    # Network patience. The health check is short on purpose: if Ollama isn't
    # up we want to know in seconds, not after a long hang.
    healthcheck_timeout_seconds: float = 5.0

    # Where the dated markdown files are written. Under data/ so .gitignore
    # already treats it as generated state.
    output_dir: Path = Path("data/news")

    # What to do when Ollama is unreachable or the model is missing:
    #   False -> still fetch and send headlines, flagged as un-summarized
    #   True  -> raise, so the scheduler logs it and Telegram alerts you
    # False by default: a headline-only digest is more useful at 07:00 than
    # no digest at all.
    require_llm: bool = False

    # How many headlines per category go into the Telegram message. The full
    # set always goes into the markdown file.
    notice_items_per_category: int = 3

    @classmethod
    def from_options(cls, options: dict[str, Any], base_dir: Path) -> "NewsConfig":
        """Build a config from a task's ``options`` block in settings.yaml.

        Anything absent from ``options`` keeps the default defined above.
        """
        defaults = cls()

        feeds = options.get("feeds") or DEFAULT_FEEDS
        # YAML gives us plain dicts/lists; copy them so a caller can't mutate
        # the module-level default by accident.
        feeds = {str(k): list(v) for k, v in feeds.items()}

        # A relative output_dir is resolved against the agent-hub folder, never
        # the current working directory — launchd starts the process from "/".
        raw_out = Path(str(options.get("output_dir", defaults.output_dir)))
        output_dir = raw_out if raw_out.is_absolute() else base_dir / raw_out

        return cls(
            feeds=feeds,
            model=str(options.get("model", defaults.model)),
            base_url=str(options.get("base_url", defaults.base_url)),
            output_mode=str(options.get("output_mode", defaults.output_mode)),
            lookback_hours=int(options.get("lookback_hours", defaults.lookback_hours)),
            item_cap_per_feed=int(
                options.get("item_cap_per_feed", defaults.item_cap_per_feed)
            ),
            category_total_cap=int(
                options.get("category_total_cap", defaults.category_total_cap)
            ),
            desc_truncate_chars=int(
                options.get("desc_truncate_chars", defaults.desc_truncate_chars)
            ),
            healthcheck_timeout_seconds=float(
                options.get(
                    "healthcheck_timeout_seconds", defaults.healthcheck_timeout_seconds
                )
            ),
            output_dir=output_dir,
            require_llm=bool(options.get("require_llm", defaults.require_llm)),
            notice_items_per_category=int(
                options.get(
                    "notice_items_per_category", defaults.notice_items_per_category
                )
            ),
        )
