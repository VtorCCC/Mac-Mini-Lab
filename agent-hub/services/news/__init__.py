"""The news digest service: fetch RSS, summarize with a local LLM, render markdown.

Ported from the standalone ``NewsDocsObtainer`` CLI. The pieces:

    config.py      what to fetch and with which limits (NewsConfig)
    models.py      pydantic schemas for the LLM output and the final digest
    fetcher.py     RSS fetch + recency filter + dedup
    summarizer.py  Ollama health check + the two pydantic-ai agents
    writer.py      DailyDigest -> markdown on disk
    digest.py      the orchestration the task actually calls

Nothing in here imports agent-hub's ``core`` package, so the service stays
testable on its own and knows nothing about scheduling or Telegram.
"""
