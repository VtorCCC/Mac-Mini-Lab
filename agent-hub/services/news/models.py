"""Pydantic schemas for the structured LLM output and the finished digest.

Two families of model live here:

  * ``CategoryLLMOutput`` / ``ItemSummary`` — what we ask the LLM to return.
    pydantic-ai validates the model's reply against these, so a malformed
    answer raises instead of quietly becoming bad output.

  * ``NewsItem`` / ``CategorySection`` / ``DailyDigest`` — the finished digest
    we render to markdown.
"""
from __future__ import annotations

from pydantic import BaseModel, Field


class ItemSummary(BaseModel):
    """One summary returned by the LLM, keyed back to a fetched item by index."""

    index: int = Field(..., description="The 1-based index of the source item from the prompt.")
    summary: str = Field(..., description="A neutral 2-3 sentence summary of the item.")


class CategoryLLMOutput(BaseModel):
    """Raw structured output returned by the category agent.

    The LLM writes *only* the overview and the per-item summaries. Titles, URLs
    and sources are taken from the fetched items by index — that's what stops
    the model from inventing links.
    """

    overview: str = Field(..., description="A 1-2 sentence category overview.")
    items: list[ItemSummary] = Field(default_factory=list)


class NewsItem(BaseModel):
    """A finished item, ready to render."""

    title: str
    url: str
    source: str
    # Empty when the digest was built without a working LLM (headlines only).
    summary: str = ""
    published: str | None = None


class CategorySection(BaseModel):
    category: str
    overview: str
    items: list[NewsItem] = Field(default_factory=list)


class DailyDigest(BaseModel):
    date: str
    overall_summary: str
    sections: list[CategorySection] = Field(default_factory=list)
    # False when Ollama was unavailable and we fell back to headlines. The task
    # uses this to say so plainly in the Telegram notice.
    summarized: bool = True
