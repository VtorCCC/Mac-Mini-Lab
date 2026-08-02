"""The news_digest task: a news briefing on Telegram every morning.

Fetches RSS feeds across four categories, summarizes them with a local LLM
(Ollama), writes a dated markdown file under ``data/news/``, and pushes a short
version to Telegram.

The actual work lives in ``services/news/`` — this file is only the wiring
between agent-hub and that library. Ported from the standalone
``NewsDocsObtainer`` CLI; see study/11-the-news-digest-task.md.
"""
from __future__ import annotations

from core.base_task import BaseTask
from core.config import task_options


class NewsDigestTask(BaseTask):
    """Builds the daily news digest and messages you the highlights."""

    name = "news_digest"

    # Default: 7:00 every morning — an hour before health_check, so the two
    # daily messages don't arrive on top of each other. Override in settings.yaml.
    schedule = {"trigger": "cron", "hour": 7, "minute": 0}

    def run(self) -> None:
        # These imports are in here, not at the top of the file, deliberately.
        # core/scheduler.py discovers tasks by importing EVERY module in tasks/
        # at startup. A top-level `import feedparser` (or pydantic_ai) would
        # mean that one missing dependency stops agent-hub from starting at all,
        # taking every other task down with it. Imported inside run(), the worst
        # case is that this single task fails inside the crash-isolation guard —
        # which is exactly what that guard is for.
        from services.news.config import NewsConfig
        from services.news.digest import chunk_message, format_notice, run

        # Everything tunable — model, feeds, lookback window — comes from the
        # `options:` block under this task in settings.yaml.
        options = task_options(self.ctx.settings, self.name)
        cfg = NewsConfig.from_options(options, self.ctx.base_dir)

        digest, path = run(cfg, self.ctx.logger)

        notice = format_notice(digest, path, cfg.notice_items_per_category)

        # A full digest easily exceeds Telegram's 4096-character cap, so the
        # notice may need to go out as several messages.
        chunks = chunk_message(notice)
        for index, chunk in enumerate(chunks, start=1):
            # Number the parts so a split briefing still reads in order.
            prefix = f"({index}/{len(chunks)})\n" if len(chunks) > 1 else ""
            self.ctx.notifier.send(prefix + chunk)

        total_items = sum(len(s.items) for s in digest.sections)
        self.ctx.logger.info(
            "News digest sent: %d items, summarized=%s, file=%s",
            total_items,
            digest.summarized,
            path,
        )
