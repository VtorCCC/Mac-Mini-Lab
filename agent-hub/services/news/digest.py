"""Orchestration: the whole digest run, start to finish.

``build_digest()`` is what the task calls. It is deliberately free of anything
agent-hub-specific — no ctx, no notifier — so it can be tested on its own and
reused by any other front end.

The run:
    1. health-check Ollama (fail fast, with an actionable message)
    2. fetch + filter each category's feeds
    3. summarize each category, then synthesize across them
    4. return a DailyDigest for the caller to write and announce
"""
from __future__ import annotations

import logging
from datetime import date
from pathlib import Path

from services.news.config import NewsConfig
from services.news.fetcher import RawItem, fetch_category
from services.news.models import CategorySection, DailyDigest
from services.news.summarizer import (
    OllamaUnavailableError,
    build_category_agent,
    build_synthesis_agent,
    headlines_section,
    ollama_healthcheck,
    summarize_category,
    synthesize_overall,
)
from services.news.writer import write_digest

log = logging.getLogger("agent-hub.news")

# Telegram rejects messages over 4096 characters. Leave headroom so a chunk
# marker or an emoji (which costs more than one byte) can't push us over.
TELEGRAM_LIMIT = 3800

_NO_LLM_OVERVIEW = "(headlines only — the local LLM was unavailable)"


def _fetch_all(cfg: NewsConfig, logger: logging.Logger) -> list[tuple[str, list[RawItem]]]:
    """Fetch every category, in the order they appear in the config."""
    results: list[tuple[str, list[RawItem]]] = []
    for category, urls in cfg.feeds.items():
        logger.info("Fetching category: %s", category)
        items = fetch_category(
            urls=urls,
            cap_per_feed=cfg.item_cap_per_feed,
            lookback_hours=cfg.lookback_hours,
            category_cap=cfg.category_total_cap,
            truncate=cfg.desc_truncate_chars,
        )
        logger.info("  -> %d items after filter+dedup", len(items))
        results.append((category, items))
    return results


def build_digest(cfg: NewsConfig, logger: logging.Logger | None = None) -> DailyDigest:
    """Run the full pipeline and return the digest.

    Raises ``OllamaUnavailableError`` only when ``cfg.require_llm`` is true;
    otherwise an unavailable LLM downgrades the run to headlines and is
    recorded on the digest as ``summarized=False``.
    """
    logger = logger or log

    # 1) Is the LLM usable? Decide once, up front.
    llm_available = True
    try:
        ollama_healthcheck(cfg.base_url, cfg.model, cfg.healthcheck_timeout_seconds)
        logger.info("Ollama reachable; model %s available", cfg.model)
    except OllamaUnavailableError as exc:
        if cfg.require_llm:
            raise
        llm_available = False
        logger.warning("Falling back to headlines only — %s", exc)

    # 2) Fetch first. Feeds are cheap compared to the LLM, and doing this
    #    before any model work means a headlines-only run costs one pass.
    fetched = _fetch_all(cfg, logger)

    # 3) Summarize, or don't.
    sections: list[CategorySection] = []
    overviews: list[tuple[str, str]] = []

    if llm_available:
        category_agent = build_category_agent(cfg.model, cfg.base_url, cfg.output_mode)
        for category, items in fetched:
            logger.info("Summarizing category: %s", category)
            section = summarize_category(category_agent, category, items)
            sections.append(section)
            overviews.append((category, section.overview))
    else:
        sections = [
            headlines_section(category, items, _NO_LLM_OVERVIEW)
            for category, items in fetched
        ]

    total_items = sum(len(s.items) for s in sections)

    # 4) The opening paragraph.
    if not total_items:
        overall = "No fresh items in the lookback window."
    elif llm_available:
        overall = synthesize_overall(build_synthesis_agent(cfg.model, cfg.base_url), overviews)
    else:
        overall = _NO_LLM_OVERVIEW

    logger.info("Digest built: %d items across %d sections", total_items, len(sections))

    return DailyDigest(
        date=date.today().isoformat(),
        overall_summary=overall,
        sections=sections,
        summarized=llm_available,
    )


def run(cfg: NewsConfig, logger: logging.Logger | None = None) -> tuple[DailyDigest, Path]:
    """Build the digest and write it to disk. Returns both."""
    logger = logger or log
    digest = build_digest(cfg, logger)
    path = write_digest(digest, cfg.output_dir, cfg.model)
    logger.info("Wrote digest to %s", path)
    return digest, path


# -----------------------------------------------------------------------------
# Turning a digest into the Telegram message.
# -----------------------------------------------------------------------------

def format_notice(digest: DailyDigest, path: Path, items_per_category: int) -> str:
    """A short, plain-text version of the digest for the morning push.

    Plain text on purpose: ``core/notifier.py`` sends without a parse_mode, so
    markdown wouldn't render. Telegram auto-links bare URLs, which is all we
    need.
    """
    parts: list[str] = [f"📰 News digest — {digest.date}"]

    if not digest.summarized:
        parts.append("⚠️ Local LLM unavailable — headlines only, no summaries.")

    parts.append(digest.overall_summary)

    for section in digest.sections:
        if not section.items:
            parts.append(f"▸ {section.category} — nothing new")
            continue

        block = [f"▸ {section.category} — {len(section.items)} items"]
        for item in section.items[:items_per_category]:
            block.append(f"• {item.title}\n  {item.url}")
        remaining = len(section.items) - items_per_category
        if remaining > 0:
            block.append(f"  …and {remaining} more")
        parts.append("\n".join(block))

    parts.append(f"📄 Full digest: {path}")
    return "\n\n".join(parts)


def chunk_message(text: str, limit: int = TELEGRAM_LIMIT) -> list[str]:
    """Split a long message into Telegram-sized pieces.

    Splits on blank lines so a chunk never cuts a headline in half. A single
    paragraph longer than the limit (rare — it would be a very long title) is
    hard-split as a last resort.
    """
    if len(text) <= limit:
        return [text]

    chunks: list[str] = []
    current = ""

    for paragraph in text.split("\n\n"):
        # A paragraph that can't fit anywhere: flush, then cut it up.
        if len(paragraph) > limit:
            if current:
                chunks.append(current)
                current = ""
            for i in range(0, len(paragraph), limit):
                chunks.append(paragraph[i : i + limit])
            continue

        candidate = f"{current}\n\n{paragraph}" if current else paragraph
        if len(candidate) > limit:
            chunks.append(current)
            current = paragraph
        else:
            current = candidate

    if current:
        chunks.append(current)
    return chunks
