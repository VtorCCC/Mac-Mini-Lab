# 08 · Logging

Logs are agent-hub's diary. When something works (or doesn't), the log tells you
what happened and when. On a machine that runs unattended 24/7, good logs are
how you find out what your program did while you weren't looking.

## Where the logs are

- **`logs/agent-hub.log`** — the app's own log (what you'll read most).
- **`logs/launchd.err.log`** and **`logs/launchd.out.log`** — created by launchd
  on the Mac; useful for startup problems (see [07 – launchd](07-launchd-and-the-mac.md)).

Logs also print to your **screen** when you run `python main.py` in a terminal.

## Reading a log line

Each line looks like:

```
2026-07-21 08:00:00,123 | INFO     | agent-hub | Running task 'health_check'...
```

That's: **timestamp** | **level** | **which logger** | **message**.

## Log levels

The "level" says how important a message is. From least to most severe:

| Level | Use it for |
|-------|------------|
| `DEBUG` | Fine-grained detail, only useful while troubleshooting |
| `INFO` | Normal events ("task started", "task finished OK") |
| `WARNING` | Something odd but survivable ("Telegram not configured") |
| `ERROR` | Something failed (a task raised an exception) |

You set the minimum level shown in `settings.yaml`:

```yaml
log_level: "INFO"    # show INFO and above (INFO, WARNING, ERROR)
```

Set it to `DEBUG` when you're chasing a problem and want maximum detail; set it
back to `INFO` for normal running.

## Rotation (why the log doesn't grow forever)

agent-hub uses a **rotating** log. When `agent-hub.log` reaches about 1 MB, it's
renamed to `agent-hub.log.1`, and a fresh `agent-hub.log` starts. This repeats,
keeping up to 5 old files (`.1` … `.5`) before the oldest is discarded. So the
logs use at most ~6 MB total — they'll never fill your disk. The sizes are set
in [`core/logging_setup.py`](../core/logging_setup.py) (`_MAX_BYTES`,
`_BACKUP_COUNT`) if you ever want to change them.

## Handy commands

```bash
tail -f logs/agent-hub.log            # follow the log live (Ctrl+C to stop)
tail -n 50 logs/agent-hub.log         # the last 50 lines
grep ERROR logs/agent-hub.log         # just the errors
grep health_check logs/agent-hub.log  # everything about one task
```

## Logging from your own task

Inside any task's `run()`:

```python
self.ctx.logger.info("Fetched %d items.", count)
self.ctx.logger.warning("Server was slow to respond.")
self.ctx.logger.error("Could not reach the API.")
```

Tip: pass values as extra arguments (the `%d`, `%s` style) rather than building
the string yourself — it's the conventional, slightly safer way to log.
