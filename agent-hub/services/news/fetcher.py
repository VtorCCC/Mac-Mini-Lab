"""RSS fetching, filtering, and deduplication.

Turns feed entries into ``RawItem`` objects with plaintext descriptions,
drops anything older than the lookback window, removes duplicate URLs, and
caps the result so the LLM prompt stays a sensible size.

A feed that fails is logged and skipped — one dead feed must not cost you the
whole morning's digest.
"""
from __future__ import annotations

import logging
import re
import socket
import ssl
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from time import mktime
from urllib.parse import urlparse
from urllib.request import HTTPSHandler

import certifi
import feedparser
from dateutil import parser as dateparser

log = logging.getLogger("agent-hub.news.fetcher")

# Verifying an HTTPS certificate needs a list of trusted authorities. `requests`
# (which core/notifier.py uses for Telegram) ships its own copy — the certifi
# package — and points OpenSSL straight at it, so it works anywhere. feedparser
# goes through urllib instead, which asks OpenSSL for the *system* default: on
# Windows that reads the OS certificate store and works fine, but on a macOS
# python.org build it points at a directory that stays empty until you run
# "Install Certificates.command". The result is that every feed fails with
# CERTIFICATE_VERIFY_FAILED while Telegram keeps working — which is exactly how
# this surfaced on the Mac mini. Handing urllib the same bundle requests already
# uses makes both paths behave identically on every machine.
_SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where())

# feedparser takes no timeout argument, so without this a feed that accepts the
# connection and then goes silent would stall the 07:00 run indefinitely.
_FEED_TIMEOUT_SECONDS = 15

_HTML_TAG_RE = re.compile(r"<[^>]+>")
_WHITESPACE_RE = re.compile(r"\s+")

# Items with no date at all sort to the bottom rather than crashing the sort.
_OLDEST = datetime.min.replace(tzinfo=timezone.utc)


@dataclass
class RawItem:
    """One entry as it came off a feed, before the LLM has seen it."""

    title: str
    url: str
    source: str
    description: str
    published: datetime | None


def _strip_html(s: str) -> str:
    """Feed descriptions are usually HTML; the LLM only needs the words."""
    return _WHITESPACE_RE.sub(" ", _HTML_TAG_RE.sub(" ", s)).strip()


def _truncate(s: str, limit: int) -> str:
    if len(s) <= limit:
        return s
    return s[: limit - 1].rstrip() + "…"


def _parse_entry_date(entry) -> datetime | None:
    """Get a timezone-aware datetime out of a feed entry, or None.

    Feeds are inconsistent, so we try the pre-parsed struct_time first and fall
    back to parsing the raw string. Anything without a timezone is assumed UTC.
    """
    parsed = entry.get("published_parsed") or entry.get("updated_parsed")
    if parsed is not None:
        try:
            return datetime.fromtimestamp(mktime(parsed), tz=timezone.utc)
        except (TypeError, ValueError, OverflowError):
            pass

    raw = entry.get("published") or entry.get("updated")
    if raw:
        try:
            dt = dateparser.parse(raw)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except (ValueError, TypeError, OverflowError):
            return None
    return None


def _feed_source(parsed_feed, fallback_url: str) -> str:
    """A human-readable name for the feed, e.g. "The Verge"."""
    title = getattr(parsed_feed.feed, "title", "") if parsed_feed.feed else ""
    if title:
        return title.strip()
    return urlparse(fallback_url).hostname or fallback_url


def fetch_feed(url: str, cap: int, truncate: int) -> list[RawItem]:
    """Fetch one feed and return up to ``cap`` of its newest items."""
    # A fresh handler per call: urllib overwrites a handler's .parent when it
    # joins an opener, and feedparser builds a new opener on every parse(). The
    # context is read-only in practice, so that part is safe to share.
    handler = HTTPSHandler(context=_SSL_CONTEXT)

    # setdefaulttimeout is process-global, so restore the old value afterwards
    # instead of quietly imposing our timeout on every other task in the hub.
    previous_timeout = socket.getdefaulttimeout()
    socket.setdefaulttimeout(_FEED_TIMEOUT_SECONDS)
    try:
        parsed = feedparser.parse(url, handlers=[handler])
    except Exception as exc:  # feedparser rarely raises, but be defensive
        log.warning("feed parse failed: %s — %s", url, exc)
        return []
    finally:
        socket.setdefaulttimeout(previous_timeout)

    # bozo=1 means the feed was malformed. If we still got entries out of it,
    # use them; if not, there's nothing to salvage.
    if parsed.bozo and not parsed.entries:
        log.warning("feed returned no entries: %s (%s)", url, parsed.bozo_exception)
        return []

    source = _feed_source(parsed, url)
    items: list[RawItem] = []
    for entry in parsed.entries:
        title = (entry.get("title") or "").strip()
        link = (entry.get("link") or "").strip()
        if not title or not link:
            continue
        description_raw = entry.get("summary") or entry.get("description") or ""
        items.append(
            RawItem(
                title=title,
                url=link,
                source=source,
                description=_truncate(_strip_html(description_raw), truncate),
                published=_parse_entry_date(entry),
            )
        )

    items.sort(key=lambda i: i.published or _OLDEST, reverse=True)
    return items[:cap]


def fetch_category(
    urls: list[str],
    cap_per_feed: int,
    lookback_hours: int,
    category_cap: int,
    truncate: int,
) -> list[RawItem]:
    """Fetch every feed in a category, then filter to recent, dedupe, and cap."""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=lookback_hours)

    collected: list[RawItem] = []
    for url in urls:
        try:
            collected.extend(fetch_feed(url, cap_per_feed, truncate))
        except Exception as exc:
            log.warning("feed fetch failed: %s — %s", url, exc)

    # Keep undated items: a missing date is a feed quirk, not evidence of age.
    fresh = [i for i in collected if i.published is None or i.published >= cutoff]

    seen: set[str] = set()
    deduped: list[RawItem] = []
    for item in fresh:
        if item.url in seen:
            continue
        seen.add(item.url)
        deduped.append(item)

    deduped.sort(key=lambda i: i.published or _OLDEST, reverse=True)
    return deduped[:category_cap]
