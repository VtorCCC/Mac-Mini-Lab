"""Talking to the local LLM: the Ollama health check and the two agents.

We use Ollama's OpenAI-compatible endpoint through pydantic-ai. There are two
agents:

  * the **category agent** summarizes one category's items, and
  * the **synthesis agent** writes the short cross-category paragraph.

One category call per category plus one synthesis call = 5 LLM calls per run
with the default four categories.

**Difference from the original CLI:** that version printed an error and called
``sys.exit(2)`` when Ollama was unreachable. That would be fatal here —
``SystemExit`` inherits from ``BaseException``, so it slips past the
``except Exception`` guard in ``core/scheduler.py`` and would take the whole
agent-hub process down with it. Everything in this module raises instead.
"""
from __future__ import annotations

import logging
from urllib.parse import urlparse

import requests
from pydantic_ai import Agent, NativeOutput, PromptedOutput
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

from services.news.config import DEFAULT_OUTPUT_MODE, OUTPUT_MODES
from services.news.fetcher import RawItem
from services.news.models import CategoryLLMOutput, CategorySection, NewsItem

log = logging.getLogger("agent-hub.news.summarizer")

CATEGORY_SYSTEM_PROMPT = (
    "You are a precise news-digest assistant. "
    "You will receive a category name and a numbered list of items. "
    "Write a 1-2 sentence overview for the category. "
    "For each item, write a neutral 2-3 sentence summary based only on the provided description. "
    "Do not invent facts. If the description is sparse, say so briefly. "
    "Return your answer as structured JSON with fields `overview` and `items`, "
    "where each item has the original `index` and your `summary`."
)

SYNTHESIS_SYSTEM_PROMPT = (
    "You write concise editorial syntheses. "
    "Given short overviews for several news categories, produce a 3-5 sentence "
    "neutral synthesis of the day's news across all categories. "
    "Do not invent specific facts; speak at the level of themes."
)

NO_ITEMS_OVERVIEW = "No items in the lookback window."


class OllamaUnavailableError(RuntimeError):
    """Ollama isn't reachable, or the requested model isn't pulled.

    Carries a message that tells you how to fix it, because it may well arrive
    as a Telegram alert at seven in the morning.
    """


def _tags_url_from_base(base_url: str) -> str:
    """Derive http://host:port/api/tags from the /v1 base URL."""
    parsed = urlparse(base_url)
    return f"{parsed.scheme}://{parsed.netloc}/api/tags"


def _model_is_available(available: set[str], model_name: str) -> bool:
    if model_name in available:
        return True
    # Ollama reports tags as "gemma3:latest". Accept a bare "gemma3" as meaning
    # that, so settings.yaml doesn't have to spell out the suffix.
    if ":" not in model_name and f"{model_name}:latest" in available:
        return True
    return False


def ollama_healthcheck(base_url: str, model_name: str, timeout: float) -> None:
    """Check Ollama is up and the model is pulled. Raise if not.

    Called before any LLM work so we fail fast with an actionable message
    rather than part-way through a run.
    """
    tags_url = _tags_url_from_base(base_url)
    try:
        response = requests.get(tags_url, timeout=timeout)
        response.raise_for_status()
        payload = response.json()
    except Exception as exc:
        raise OllamaUnavailableError(
            f"Cannot reach Ollama at {base_url} — is `ollama serve` running? ({exc})"
        ) from exc

    # Ollama lists each model under "name"; some versions also set "model".
    available = {
        str(m.get("name") or m.get("model") or "")
        for m in payload.get("models", [])
    }
    available.discard("")

    if not _model_is_available(available, model_name):
        raise OllamaUnavailableError(
            f"Model {model_name!r} is not pulled. "
            f"Available: {sorted(available) or '(none)'}. "
            f"Fix with: ollama pull {model_name}"
        )


def build_model(model_name: str, base_url: str) -> OpenAIChatModel:
    # Ollama ignores the API key but the OpenAI client insists on one.
    return OpenAIChatModel(
        model_name,
        provider=OpenAIProvider(base_url=base_url, api_key="ollama"),
    )


def _apply_output_mode(output_type: type, mode: str):
    """Wrap the schema in the marker pydantic-ai uses for that output mode.

    Which mode works depends on the model, and with local models the spread is
    wide. Measured against Ollama on 2026-08-02:

        mode      | gemma3:latest              | gpt-oss:20b
        ----------|----------------------------|------------
        native    | works                      | works
        tool      | 400 "does not support tools" | works
        prompted  | exceeded output retries    | works

    "native" asks Ollama to constrain output to the JSON schema, which needs no
    tool support — hence the default. Switch modes in settings.yaml if the
    model on the Mac mini prefers another one.
    """
    if mode == "native":
        return NativeOutput(output_type)
    if mode == "prompted":
        return PromptedOutput(output_type)
    if mode == "tool":
        # Plain schema = pydantic-ai's default, which is tool calling.
        return output_type
    raise ValueError(
        f"Unknown output_mode {mode!r}. Choose one of: {', '.join(OUTPUT_MODES)}"
    )


def build_category_agent(
    model_name: str,
    base_url: str,
    output_mode: str = DEFAULT_OUTPUT_MODE,
) -> Agent[None, CategoryLLMOutput]:
    return Agent(
        build_model(model_name, base_url),
        output_type=_apply_output_mode(CategoryLLMOutput, output_mode),
        system_prompt=CATEGORY_SYSTEM_PROMPT,
    )


def build_synthesis_agent(model_name: str, base_url: str) -> Agent[None, str]:
    # No output mode needed here: this agent returns ordinary prose, so there's
    # no JSON schema to constrain and every model can manage it.
    return Agent(
        build_model(model_name, base_url),
        output_type=str,
        system_prompt=SYNTHESIS_SYSTEM_PROMPT,
    )


def _format_items_prompt(category: str, items: list[RawItem]) -> str:
    """Number the items so the LLM can refer back to them by index."""
    blocks: list[str] = [f"Category: {category}", "", "Items:"]
    for idx, item in enumerate(items, start=1):
        blocks.append(
            f"[{idx}] {item.title} | source: {item.source}\n"
            f"    desc: {item.description or '(no description provided)'}"
        )
    return "\n".join(blocks)


def to_news_item(raw: RawItem, summary: str = "") -> NewsItem:
    """Convert a fetched item into a finished one, keeping the real URL."""
    return NewsItem(
        title=raw.title,
        url=raw.url,
        source=raw.source,
        summary=summary,
        published=raw.published.isoformat() if raw.published else None,
    )


def headlines_section(category: str, items: list[RawItem], overview: str) -> CategorySection:
    """A section with no LLM involvement — titles, sources and links only.

    Used both when Ollama is unavailable and when a single category's LLM call
    fails after a retry.
    """
    return CategorySection(
        category=category,
        overview=overview if items else NO_ITEMS_OVERVIEW,
        items=[to_news_item(i) for i in items],
    )


def summarize_category(
    agent: Agent[None, CategoryLLMOutput],
    category: str,
    items: list[RawItem],
) -> CategorySection:
    """Summarize one category with a single LLM call, retried once.

    If both attempts fail we degrade to headlines for this category rather than
    raising: three good sections and one bare one beats no digest.
    """
    if not items:
        return CategorySection(category=category, overview=NO_ITEMS_OVERVIEW, items=[])

    prompt = _format_items_prompt(category, items)

    output: CategoryLLMOutput | None = None
    last_exc: Exception | None = None
    for attempt in (1, 2):
        try:
            output = agent.run_sync(prompt).output
            break
        except Exception as exc:
            last_exc = exc
            log.warning("LLM call failed for %s (attempt %d): %s", category, attempt, exc)

    if output is None:
        log.error("giving up on category %s after retry: %s", category, last_exc)
        return headlines_section(category, items, "(summarization failed)")

    # Zip the summaries back onto the fetched items by index. Anything the
    # model skipped simply has no summary — we never drop or invent an item.
    summaries_by_index = {s.index: s.summary for s in output.items}
    news_items = [
        to_news_item(raw, summaries_by_index.get(idx, ""))
        for idx, raw in enumerate(items, start=1)
    ]
    return CategorySection(category=category, overview=output.overview, items=news_items)


def synthesize_overall(
    agent: Agent[None, str],
    overviews: list[tuple[str, str]],
) -> str:
    """Write the paragraph that opens the digest, from the category overviews."""
    body = "\n\n".join(f"{cat}: {ov}" for cat, ov in overviews if ov)
    if not body:
        return "No fresh items in the lookback window."
    try:
        return agent.run_sync(body).output.strip()
    except Exception as exc:
        log.warning("synthesis call failed: %s", exc)
        return "(cross-category synthesis failed; see the sections below)"
