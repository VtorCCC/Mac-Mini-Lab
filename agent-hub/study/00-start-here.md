# 00 · Start here

Welcome! This folder is a small course built around **your own project**. The
goal: after reading these, you can confidently change how agent-hub works and
add your own tasks — without feeling lost.

You do **not** need to read everything at once. Here's a sensible order.

## If you have 5 minutes

Read this page, then skim
[01 – How the project fits together](01-how-the-project-fits-together.md).

## The 5-minute mental model

agent-hub is **one program that runs forever** and does jobs on a timer.

Think of it like an office with:

- **A manager (the "scheduler")** who holds a calendar and, at the right time,
  taps a worker on the shoulder and says "go." That's
  [`core/scheduler.py`](../core/scheduler.py).
- **Workers (the "tasks")** who each know how to do one job. Right now there's
  one worker, `health_check`, who every morning reports how things are going.
  Workers live in [`tasks/`](../tasks/).
- **A notebook (the "storage")** where every completed job is written down, so
  we can answer "how many jobs ran yesterday?" That's
  [`core/storage.py`](../core/storage.py).
- **A messenger (the "notifier")** who texts you on Telegram when something
  important happens. That's [`core/notifier.py`](../core/notifier.py).
- **A logbook (the "logs")** — a running diary of everything that happened,
  saved to files in [`logs/`](../logs/).

The manager is careful: if a worker trips and falls (throws an error), the
manager writes it in the notebook, texts you, and **keeps the office open**. One
broken job never shuts everything down. That safety net is the single most
important idea in this project.

## What to read next, by goal

| I want to… | Read |
|------------|------|
| Understand the whole thing | [01 – How the project fits together](01-how-the-project-fits-together.md) |
| Understand the Python I'm seeing | [02 – Python concepts used](02-python-concepts-used.md) |
| Change *when* a task runs | [03 – APScheduler & cron](03-apscheduler-and-cron.md) |
| **Add my own task** | [04 – Adding a new task](04-adding-a-new-task.md) |
| Look at the recorded run history | [05 – SQLite storage](05-sqlite-storage.md) |
| Get Telegram messages working | [06 – Telegram setup](06-telegram-setup.md) |
| Keep it running 24/7 | [07 – launchd & the Mac](07-launchd-and-the-mac.md) |
| Find/read the logs | [08 – Logging](08-logging.md) |
| Fix something that's broken | [09 – Troubleshooting / FAQ](09-troubleshooting-faq.md) |
| Look up a word I don't know | [10 – Glossary](10-glossary.md) |
| See a real task, warts and all | [11 – The news digest task](11-the-news-digest-task.md) |

## Two commands to remember

```bash
python main.py --list                    # what tasks exist, and when they run
python main.py --run-once health_check   # run a task NOW, to see it work
```

These let you experiment safely without waiting for a real scheduled time.
