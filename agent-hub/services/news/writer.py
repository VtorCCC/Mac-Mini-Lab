"""Render a DailyDigest to markdown and write it to a dated file.

Output goes to ``<output_dir>/YYYY-MM-DD.md``. Re-running on the same day
overwrites that day's file, which makes the task safe to run twice (say, after
a failure) without piling up duplicates.
"""
from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

from services.news.models import DailyDigest

_EMPTY_CATEGORY_LINE = "_No items in the lookback window._"
_WHITESPACE_RE = re.compile(r"\s+")


def _blockquote(text: str) -> str:
    """Prefix every line with "> ".

    Markdown needs the marker on each line: LLM output is often several
    paragraphs, and quoting only the first line leaves the rest as body text.
    """
    lines = text.strip().splitlines() or [""]
    return "\n".join(f"> {line.strip()}" if line.strip() else ">" for line in lines)


def _one_line(text: str) -> str:
    """Collapse to a single line, so wrapping it in _..._ can't break the emphasis."""
    return _WHITESPACE_RE.sub(" ", text).strip()


def render_markdown(digest: DailyDigest, model_name: str) -> str:
    generated_at = datetime.now().astimezone().isoformat(timespec="seconds")
    lines: list[str] = []

    # YAML front matter, so the file is readable by note apps like Obsidian.
    lines.append("---")
    lines.append(f"date: {digest.date}")
    lines.append(f"generated_at: {generated_at}")
    lines.append(f"model: {model_name if digest.summarized else 'none (headlines only)'}")
    lines.append(f"summarized: {str(digest.summarized).lower()}")
    lines.append("---")
    lines.append("")
    lines.append(f"# News Digest — {digest.date}")
    lines.append("")

    if not digest.summarized:
        lines.append(
            "> ⚠️ The local LLM was unavailable for this run, so these are "
            "headlines without summaries."
        )
        lines.append("")

    lines.append(_blockquote(digest.overall_summary))
    lines.append("")

    for section in digest.sections:
        lines.append(f"## {section.category}")
        lines.append("")
        if not section.items:
            lines.append(_EMPTY_CATEGORY_LINE)
            lines.append("")
            continue
        if section.overview:
            lines.append(f"_{_one_line(section.overview)}_")
            lines.append("")
        for idx, item in enumerate(section.items):
            lines.append(f"### [{item.title}]({item.url})")
            meta = f"**Source:** {item.source}"
            if item.published:
                meta += f" — _published_: {item.published}"
            lines.append(meta)
            lines.append("")
            # A headlines-only run has no summary; skip the blank paragraph.
            if item.summary:
                lines.append(item.summary)
                lines.append("")
            if idx < len(section.items) - 1:
                lines.append("---")
                lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def write_digest(digest: DailyDigest, out_dir: Path, model_name: str) -> Path:
    """Write the digest and return the path it landed at."""
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{digest.date}.md"
    path.write_text(render_markdown(digest, model_name), encoding="utf-8")
    return path
