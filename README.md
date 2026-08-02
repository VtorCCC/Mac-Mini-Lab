# Macmini-lab

Studying how to use Claude Code with GitHub, and repo draft store here.

A collection of small, independent projects that run on a Mac mini kept on 24/7
— plus the notes made while building them.

## Components

- [`agent-hub/`](agent-hub/) — an always-on Python process that hosts scheduled
  tasks (APScheduler + `launchd`), with a beginner-friendly
  [`study/`](agent-hub/study/) guide series. Currently hosts a daily
  `health_check` and a `news_digest` that summarizes the morning's RSS with a
  local LLM and messages it to Telegram.

## Tracking

- [`STATUS.md`](STATUS.md) — where everything stands right now.
- [`WORKLOG.md`](WORKLOG.md) — dated history of what was done and why.
- [`CLAUDE.md`](CLAUDE.md) — how Claude Code should work in this repo.
