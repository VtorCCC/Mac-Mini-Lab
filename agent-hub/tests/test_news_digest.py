"""Tests for the news_digest task and the services/news library.

These run offline: no RSS is fetched and no LLM is called. What they protect is
the wiring — config resolution, the no-LLM fallback, Telegram chunking, and the
one behaviour that could hurt the whole app: an unreachable Ollama must raise a
normal Exception, never SystemExit.

The happy path (a real model actually summarizing) needs Ollama running and is
covered by `python main.py --run-once news_digest` instead.
"""
from datetime import datetime, timezone
from pathlib import Path

import pytest

from core.base_task import BaseTask
from core.config import task_options
from core.context import AppContext
from core.logging_setup import setup_logging
from core.notifier import TelegramNotifier
from core.scheduler import AgentScheduler, discover_task_classes
from core.storage import Storage
from services.news import digest as digest_module
from services.news import summarizer
from services.news.config import NewsConfig
from services.news.digest import build_digest, chunk_message, format_notice
from services.news.fetcher import RawItem
from services.news.models import CategorySection, DailyDigest, NewsItem
from services.news.summarizer import OllamaUnavailableError, ollama_healthcheck
from services.news.writer import render_markdown


# -----------------------------------------------------------------------------
# Discovery + configuration
# -----------------------------------------------------------------------------

def test_news_digest_is_discovered():
    names = {cls.name for cls in discover_task_classes()}
    assert "news_digest" in names


def test_task_options_reads_the_options_block():
    settings = {"tasks": {"news_digest": {"options": {"model": "llama3.2:latest"}}}}
    assert task_options(settings, "news_digest") == {"model": "llama3.2:latest"}
    # A task with no options must still give callers a dict to .get() from.
    assert task_options(settings, "health_check") == {}


def test_config_overrides_apply_and_defaults_survive():
    cfg = NewsConfig.from_options({"model": "qwen3:latest", "lookback_hours": 48}, Path("/base"))
    assert cfg.model == "qwen3:latest"
    assert cfg.lookback_hours == 48
    # Untouched values keep their defaults.
    assert cfg.item_cap_per_feed == NewsConfig().item_cap_per_feed
    assert "World" in cfg.feeds


def test_relative_output_dir_resolves_against_base_dir():
    # launchd starts the process from "/", so a relative path must never be
    # interpreted against the working directory.
    cfg = NewsConfig.from_options({"output_dir": "data/news"}, Path("/base"))
    assert cfg.output_dir == Path("/base/data/news")

    absolute = NewsConfig.from_options({"output_dir": "/tmp/elsewhere"}, Path("/base"))
    assert absolute.output_dir == Path("/tmp/elsewhere")


def test_config_does_not_share_the_default_feed_dict():
    cfg = NewsConfig.from_options({}, Path("/base"))
    cfg.feeds["World"].append("https://example.com/rss")
    fresh = NewsConfig.from_options({}, Path("/base"))
    assert "https://example.com/rss" not in fresh.feeds["World"]


# -----------------------------------------------------------------------------
# The health check must raise, not exit
# -----------------------------------------------------------------------------

def test_unreachable_ollama_raises_a_catchable_exception(monkeypatch):
    """The original CLI called sys.exit(2) here.

    SystemExit inherits from BaseException, so it would slip past the
    `except Exception` guard in core/scheduler.py and kill the whole process.
    """
    def _boom(*args, **kwargs):
        raise OSError("connection refused")

    monkeypatch.setattr(summarizer.requests, "get", _boom)

    with pytest.raises(OllamaUnavailableError) as excinfo:
        ollama_healthcheck("http://localhost:11434/v1", "gemma3:latest", 1.0)

    assert isinstance(excinfo.value, Exception)  # i.e. crash isolation catches it


def test_missing_model_is_reported_with_the_fix(monkeypatch):
    class _Response:
        def raise_for_status(self):
            pass

        def json(self):
            return {"models": [{"name": "llama3.2:latest"}]}

    monkeypatch.setattr(summarizer.requests, "get", lambda *a, **k: _Response())

    with pytest.raises(OllamaUnavailableError, match="ollama pull gemma3:latest"):
        ollama_healthcheck("http://localhost:11434/v1", "gemma3:latest", 1.0)


def test_output_mode_selects_the_right_pydantic_ai_marker():
    from pydantic_ai import NativeOutput, PromptedOutput

    from services.news.models import CategoryLLMOutput
    from services.news.summarizer import _apply_output_mode

    assert isinstance(_apply_output_mode(CategoryLLMOutput, "native"), NativeOutput)
    assert isinstance(_apply_output_mode(CategoryLLMOutput, "prompted"), PromptedOutput)
    # "tool" is pydantic-ai's default, i.e. the bare schema.
    assert _apply_output_mode(CategoryLLMOutput, "tool") is CategoryLLMOutput


def test_a_typo_in_output_mode_fails_with_the_valid_choices():
    from services.news.models import CategoryLLMOutput
    from services.news.summarizer import _apply_output_mode

    with pytest.raises(ValueError, match="native"):
        _apply_output_mode(CategoryLLMOutput, "nativ")


def test_default_output_mode_is_the_portable_one():
    # "native" is the only mode that worked on a model without tool support.
    assert NewsConfig().output_mode == "native"
    assert NewsConfig.from_options({"output_mode": "tool"}, Path("/base")).output_mode == "tool"


def test_bare_model_name_matches_the_latest_tag(monkeypatch):
    class _Response:
        def raise_for_status(self):
            pass

        def json(self):
            return {"models": [{"name": "gemma3:latest"}]}

    monkeypatch.setattr(summarizer.requests, "get", lambda *a, **k: _Response())
    # "gemma3" should be accepted as meaning "gemma3:latest".
    ollama_healthcheck("http://localhost:11434/v1", "gemma3", 1.0)


# -----------------------------------------------------------------------------
# The no-LLM fallback
# -----------------------------------------------------------------------------

def _fake_items(n: int = 2) -> list[RawItem]:
    return [
        RawItem(
            title=f"Headline {i}",
            url=f"https://example.com/{i}",
            source="Example News",
            description="Some description.",
            published=datetime(2026, 8, 2, 6, 0, tzinfo=timezone.utc),
        )
        for i in range(n)
    ]


@pytest.fixture
def offline_feeds(monkeypatch):
    """Replace the network fetch with fixed items."""
    monkeypatch.setattr(digest_module, "fetch_category", lambda **kwargs: _fake_items())


@pytest.fixture
def ollama_down(monkeypatch):
    def _raise(*args, **kwargs):
        raise OllamaUnavailableError("Ollama is not running")

    monkeypatch.setattr(digest_module, "ollama_healthcheck", _raise)


def test_digest_falls_back_to_headlines_when_ollama_is_down(offline_feeds, ollama_down):
    cfg = NewsConfig.from_options({"require_llm": False}, Path("/base"))
    result = build_digest(cfg)

    assert result.summarized is False
    assert result.sections, "sections should still be produced"
    # Real headlines and links survive; only the summaries are missing.
    first = result.sections[0].items[0]
    assert first.title == "Headline 0"
    assert first.url == "https://example.com/0"
    assert first.summary == ""


def test_require_llm_turns_an_unavailable_ollama_into_a_failure(offline_feeds, ollama_down):
    cfg = NewsConfig.from_options({"require_llm": True}, Path("/base"))
    with pytest.raises(OllamaUnavailableError):
        build_digest(cfg)


def test_headlines_only_digest_writes_readable_markdown():
    digest = DailyDigest(
        date="2026-08-02",
        overall_summary="(headlines only)",
        summarized=False,
        sections=[
            CategorySection(
                category="World",
                overview="(headlines only)",
                items=[NewsItem(title="A thing happened", url="https://example.com/a", source="Example")],
            )
        ],
    )
    markdown = render_markdown(digest, "gemma3:latest")

    assert "summarized: false" in markdown
    assert "[A thing happened](https://example.com/a)" in markdown
    assert "headlines without summaries" in markdown
    # No stray blank paragraph where the summary would have been.
    assert "\n\n\n" not in markdown


def test_multi_paragraph_summary_stays_inside_the_blockquote():
    """LLMs routinely answer in several paragraphs.

    Quoting only the first line would drop the rest out of the blockquote.
    """
    digest = DailyDigest(
        date="2026-08-02",
        overall_summary="Here is a synthesis:\n\nGlobal events dominate.\nMarkets are calm.",
        sections=[],
    )
    body = render_markdown(digest, "gemma3:latest")

    quoted = [ln for ln in body.splitlines() if ln.startswith(">")]
    assert "> Global events dominate." in quoted
    assert "> Markets are calm." in quoted
    # No line of the summary escaped the quote.
    assert "\nGlobal events dominate." not in body


def test_multi_line_overview_does_not_break_italics():
    digest = DailyDigest(
        date="2026-08-02",
        overall_summary="Fine.",
        sections=[
            CategorySection(
                category="World",
                overview="First line.\nSecond line.",
                items=[NewsItem(title="T", url="https://e.com", source="E", summary="S")],
            )
        ],
    )
    body = render_markdown(digest, "gemma3:latest")
    assert "_First line. Second line._" in body


# -----------------------------------------------------------------------------
# The Telegram notice
# -----------------------------------------------------------------------------

def _digest_with(n_items: int, summarized: bool = True) -> DailyDigest:
    return DailyDigest(
        date="2026-08-02",
        overall_summary="A calm day.",
        summarized=summarized,
        sections=[
            CategorySection(
                category="World",
                overview="Things happened.",
                items=[
                    NewsItem(
                        title=f"Headline {i}",
                        url=f"https://example.com/{i}",
                        source="Example",
                        summary="A summary.",
                    )
                    for i in range(n_items)
                ],
            )
        ],
    )


def test_notice_lists_the_top_items_and_counts_the_rest():
    notice = format_notice(_digest_with(10), Path("/base/data/news/2026-08-02.md"), 3)

    assert "📰 News digest — 2026-08-02" in notice
    assert "Headline 0" in notice and "Headline 2" in notice
    assert "Headline 3" not in notice          # beyond the per-category cap
    assert "…and 7 more" in notice
    assert "2026-08-02.md" in notice


def test_notice_says_so_when_there_were_no_summaries():
    notice = format_notice(_digest_with(2, summarized=False), Path("/x.md"), 3)
    assert "headlines only" in notice.lower()


def test_short_message_is_not_chunked():
    assert chunk_message("hello") == ["hello"]


def test_long_message_is_split_within_the_limit_without_losing_content():
    paragraphs = [f"▸ Section {i}\n• Headline\n  https://example.com/{i}" for i in range(200)]
    text = "\n\n".join(paragraphs)

    chunks = chunk_message(text, limit=1000)

    assert len(chunks) > 1
    assert all(len(c) <= 1000 for c in chunks)
    # Every headline still appears somewhere.
    rejoined = "\n\n".join(chunks)
    for i in range(200):
        assert f"https://example.com/{i}" in rejoined


def test_a_single_oversized_paragraph_is_hard_split():
    chunks = chunk_message("x" * 250, limit=100)
    assert all(len(c) <= 100 for c in chunks)
    assert "".join(chunks) == "x" * 250


# -----------------------------------------------------------------------------
# The task, through the scheduler's guard
# -----------------------------------------------------------------------------

def _make_ctx(tmp_path: Path, settings: dict) -> AppContext:
    storage = Storage(tmp_path / "test.db")
    storage.init_db()
    return AppContext(
        notifier=TelegramNotifier(token=None, chat_id=None),  # no-op notifier
        storage=storage,
        logger=setup_logging(tmp_path / "logs", "INFO"),
        settings=settings,
        process_start=datetime.now(timezone.utc),
        base_dir=tmp_path,
        db_path=tmp_path / "test.db",
    )


def test_task_writes_a_file_and_records_a_successful_run(
    tmp_path, offline_feeds, ollama_down
):
    ctx = _make_ctx(tmp_path, {"tasks": {"news_digest": {"options": {"output_dir": "news-out"}}}})
    task = next(c for c in discover_task_classes() if c.name == "news_digest")(ctx)

    AgentScheduler(ctx).run_once(task)

    written = list((tmp_path / "news-out").glob("*.md"))
    assert len(written) == 1
    assert ctx.storage.count_runs_last_24h() == 1


def test_a_broken_news_digest_cannot_take_down_the_process(tmp_path, monkeypatch):
    """The load-bearing guarantee: this task failing is just a failed run."""
    def _explode(*args, **kwargs):
        raise RuntimeError("feeds are on fire")

    monkeypatch.setattr(digest_module, "run", _explode)

    ctx = _make_ctx(tmp_path, {})
    task = next(c for c in discover_task_classes() if c.name == "news_digest")(ctx)

    AgentScheduler(ctx).run_once(task)  # must not raise

    assert ctx.storage.count_runs_last_24h() == 1
    assert isinstance(task, BaseTask)
