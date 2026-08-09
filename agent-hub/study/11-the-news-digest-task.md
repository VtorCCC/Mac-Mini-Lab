# 11 · The news digest task

The first task in agent-hub that does real work. Every morning at 07:00 it:

1. fetches RSS feeds across four categories,
2. summarizes each one with a **local** LLM (Ollama on the Mac mini),
3. writes `data/news/YYYY-MM-DD.md`, and
4. Telegrams you the highlights.

It was ported from a standalone CLI (`NewsDocsObtainer`). This guide covers how
it's put together, why it's shaped this way, and what to do when it misbehaves.

---

## Where the code lives

The task file is deliberately tiny. The real work sits in a library:

```
tasks/news_digest.py        <- ~40 lines: read settings, call the library, send
services/news/
  config.py                 <- feeds, model, limits (NewsConfig)
  models.py                 <- pydantic schemas
  fetcher.py                <- RSS fetch, recency filter, dedup
  summarizer.py             <- Ollama health check + the two LLM agents
  writer.py                 <- DailyDigest -> markdown
  digest.py                 <- orchestration + the Telegram message
```

### Why a `services/` folder instead of putting it all in `tasks/`?

Because [`core/scheduler.py`](../core/scheduler.py) discovers tasks by
**importing every module in `tasks/`** at startup. That folder should stay one
small class per file. Anything bigger lives in `services/` and gets called from
the task.

---

## The three decisions worth understanding

### 1. The imports are inside `run()`, not at the top of the file

Look at `tasks/news_digest.py` and you'll see the imports sitting *inside* the
method. That looks wrong if you've been taught to put imports at the top — and
normally it would be. Here's why it isn't:

Discovery imports every task module when agent-hub boots. If `news_digest.py`
imported `feedparser` at the top and feedparser wasn't installed, **agent-hub
would not start at all** — `health_check` included. One optional dependency
would take down the whole hub.

Imported inside `run()`, the worst case is that this one task fails, gets logged,
alerts you on Telegram, and everything else carries on. That's exactly what
crash isolation is for. (See [01](01-how-the-project-fits-together.md).)

### 2. An unreachable Ollama raises — it never calls `sys.exit()`

The original CLI printed an error and called `sys.exit(2)` when Ollama was down.
Perfectly reasonable in a script. **Fatal here.**

`sys.exit()` raises `SystemExit`, and `SystemExit` inherits from `BaseException`,
not `Exception`. The guard in `core/scheduler.py` catches `Exception`:

```python
except Exception as exc:   # SystemExit is NOT caught by this
```

So a `sys.exit()` inside a task would sail straight past crash isolation and
kill the whole scheduler. Every failure path in `services/news/` raises a normal
exception instead — `OllamaUnavailableError`. There's a test pinning that
behaviour in `tests/test_news_digest.py`.

**The lesson generalises:** never call `sys.exit()` inside a task.

### 3. No LLM still means you get a digest

If Ollama is down, the task doesn't just fail. It fetches the feeds anyway and
sends you **headlines without summaries**, clearly flagged. At 07:00 a partial
briefing beats an error message.

Flip that with `require_llm: true` in `settings.yaml` if you'd rather be told
loudly that something is broken.

---

## Structured output: the fiddly part

We need the model to return *structured JSON* (an overview plus a summary per
item), not free prose. pydantic-ai can ask for that in three ways, and **which
ones work depends entirely on the model.** Measured against Ollama on
2026-08-02:

| `output_mode` | `gemma3:latest` | `gpt-oss:20b` |
|---------------|-----------------|---------------|
| `native`      | ✅ works        | ✅ works |
| `tool`        | ❌ `400 does not support tools` | ✅ works |
| `prompted`    | ❌ exceeded output retries | ✅ works |

pydantic-ai's **default is `tool`**, and that is why the first run of this task
produced "(summarization failed)" for every category: gemma3 has no tool
support.

The default here is **`native`**, which asks Ollama to constrain the output to
the JSON schema directly. It needs no tool support, so it works on the widest
range of local models. Change it in `settings.yaml` if your model prefers
another mode.

### Why the LLM can't invent links

The model is only ever asked for an `overview` and per-item `summary` values,
keyed by index. Titles, URLs and sources come from `feedparser` and are zipped
back on afterwards. A model that hallucinates a URL simply has nowhere to put
it.

---

## Configuration

Everything lives under the task's `options:` block in `settings.yaml` — no
Python edit needed to change the model, the schedule, or the feed list:

```yaml
tasks:
  news_digest:
    enabled: true
    schedule:
      trigger: cron
      hour: 7
      minute: 0
    options:
      model: "gemma3:latest"
      output_mode: "native"
      lookback_hours: 24
      require_llm: false
      feeds:
        "World":
          - "https://feeds.bbci.co.uk/news/world/rss.xml"
```

| Option | Default | What it does |
|--------|---------|--------------|
| `model` | `gemma3:latest` | Must appear in `ollama list` |
| `base_url` | `http://localhost:11434/v1` | Ollama's OpenAI-compatible endpoint |
| `output_mode` | `native` | See the table above |
| `lookback_hours` | `24` | Ignore anything older |
| `item_cap_per_feed` | `5` | Keeps the prompt bounded |
| `category_total_cap` | `15` | Max items per section |
| `notice_items_per_category` | `3` | Headlines in the Telegram message |
| `require_llm` | `false` | `true` = fail instead of degrading |
| `output_dir` | `data/news` | Relative paths resolve against `agent-hub/` |
| `feeds` | four categories | Must be real RSS/Atom URLs |

`options:` is read by the task itself via `core.config.task_options()`.
agent-hub doesn't interpret it — any task can keep its own settings there.

---

## Running it by hand

```bash
python main.py --run-once news_digest
```

Expect it to take **2–5 minutes**: it's five LLM calls (one per category plus
one synthesis) against a local model. That's normal, and it's why this is a
scheduled task rather than something you wait on.

---

## Verifying this on the Mac mini

Everything below was verified on the **Windows dev machine only**. The model and
the output mode are the two things that genuinely have to be re-proven on the
Mac, because both depend on which models Ollama has there. Work through these in
order — each step's failure has a different fix.

### 0. Install the new dependencies

This task added five (`feedparser`, `python-dateutil`, `pydantic`,
`pydantic-ai-slim`, `certifi`). Pulling the code is not enough — from
`agent-hub/`:

```bash
pip install -r requirements.txt
```

Then confirm the task is visible before going further:

```bash
python main.py --list
```

`news_digest` should appear as `enabled`. If it doesn't, nothing below matters.

### 0.5 Can it reach the feeds at all?

Every step below is about the *LLM* half. None of it matters if the *network*
half is broken, and that failure is quiet — the task still logs `finished OK`,
just with nothing in it. Check the feeds first:

```bash
python -c "from services.news.fetcher import fetch_feed; print(len(fetch_feed('https://hnrss.org/frontpage', 3, 300)))"
```

A number greater than `0` means feeds work. `0` means read the
`CERTIFICATE_VERIFY_FAILED` entry in [Troubleshooting](#troubleshooting) below —
this is the exact thing that bit the first Mac mini run.

### 1. Is Ollama there, and what does it have?

```bash
ollama list
```

Note a model name from that list. If Ollama isn't installed, install it first —
without it this task only ever produces headlines.

### 2. Does that model actually run?

```bash
ollama run <model> "Say hello in five words."
```

This is the step that caught `gemma4` on Windows: it crashed llama-server on a
plain prompt. If this fails, the model is unusable — pick another one. No
amount of config will fix it.

### 3. Point the task at it

In `settings.yaml`, set `model:` under `news_digest` → `options:` to the name
from step 1.

### 4. Does it produce *structured* output?

This is the real test, and the one that failed first time on Windows. A model
can pass step 2 and still fail here.

```bash
python main.py --run-once news_digest
```

Give it 2–5 minutes. Then:

```bash
grep -c "summarization failed" data/news/$(date +%F).md
```

- **`0`** → working. Done.
- **more than 0** → the model can't honour `output_mode: native`. Check why:

  ```bash
  grep "LLM call failed" logs/agent-hub.log | tail -3
  ```

  Then try `output_mode: "tool"` in `settings.yaml` and re-run. If neither
  works, try `"prompted"`; if none work, use a different model.

### 5. Does the Telegram briefing arrive?

The `--run-once` above should have sent it. If nothing came, confirm the bot
itself works — that's a separate problem from the digest:

```bash
python main.py --test-telegram
```

### 6. Will Ollama be up at 07:00?

**The most likely cause of a silent failure in production.** If Ollama only
starts when you log in, it won't be running when launchd fires the task on a
rebooted machine — you'll get headlines with no summaries every morning and
wonder why. Make sure it starts as a service at boot, then reboot and check:

```bash
curl -s http://localhost:11434/api/tags | head -c 200
```

If that works right after a reboot *without logging into the desktop*, you're
set. The launchd side of agent-hub itself is covered in
[07 – launchd & the Mac](07-launchd-and-the-mac.md).

### 7. Let it fire on its own

Leave it overnight and confirm the 07:00 briefing arrives unprompted. That's the
only thing that proves the whole chain — launchd, Ollama, feeds, LLM, Telegram.

---

## Troubleshooting

**`0 items` and a wall of `CERTIFICATE_VERIFY_FAILED` warnings**

The log looks like this, once per feed, and the run still ends `finished OK`:

```
WARNING | agent-hub.news.fetcher | feed returned no entries: https://hnrss.org/frontpage
         (<urlopen error [SSL: CERTIFICATE_VERIFY_FAILED] unable to get local issuer certificate>)
INFO    | agent-hub | Digest built: 0 items across 4 sections
```

This is a **certificate** problem, not a network one, and the tell is that the
Telegram message still arrives. Two different libraries do HTTPS here:

| What | Library | Where its trusted authorities come from |
|------|---------|------------------------------------------|
| Telegram (`core/notifier.py`) | `requests` | ships its own bundle — the `certifi` package |
| RSS feeds (`services/news/fetcher.py`) | `feedparser` → `urllib` | asks OpenSSL for the system default |

On Windows that system default reads the OS certificate store, so it just
works. On macOS, a python.org build points at a directory that stays **empty**
until you run its setup script — so every feed fails while Telegram is fine.
Same machine, same second, same network: that split is the whole diagnosis.

`fetcher.py` now hands `urllib` the same certifi bundle `requests` uses, so a
current checkout should not hit this at all. If you are on an older checkout, or
some other tool on the Mac shows the same error, fix the Python install itself:

```bash
/Applications/Python\ 3.11/Install\ Certificates.command
```

Adjust the version to match. If that file doesn't exist, your Python came from
Homebrew rather than python.org — use this instead:

```bash
brew install ca-certificates && pip install --upgrade certifi
```

To confirm which Python you are actually running, and whether it can see any
authorities at all:

```bash
python -c "import ssl; print(ssl.get_default_verify_paths())"
```

**Every section says "(summarization failed)"**
Your model probably doesn't support the current `output_mode`. Check the log:

```bash
grep "LLM call failed" logs/agent-hub.log
```

`does not support tools` → set `output_mode: "native"`.

**"Cannot reach Ollama … is `ollama serve` running?"**
Ollama isn't up. On the Mac mini it needs to be running as a service *before*
agent-hub fires at 07:00 — a login-only Ollama won't be there after a reboot.

**"Model 'x' is not pulled"**
Run `ollama pull x`, or point `model:` at something `ollama list` shows. Read
the name in the error carefully first — the message helpfully prints what *is*
available. `gemini` (Google's hosted model) and `gemma` (the open one you can
actually pull) are one letter apart and easy to cross; the first Mac mini run
had `gemini4:12b` in `settings.yaml` and no such model exists.

**A run that never finishes**
Feeds are fetched with a 15-second timeout (`_FEED_TIMEOUT_SECONDS` in
`services/news/fetcher.py`) precisely so one silent feed can't stall the 07:00
run forever. If you need to change it, note that it is applied by setting the
process-global default socket timeout and then putting the previous value back
— that restore is deliberate, so don't drop it.

**`llama-server process has terminated: exit status 0xc0000409`**
The model itself is crashing, not your code. Both `gemma4:latest` and
`gemma4:e4b` do this on the Windows dev machine even for a plain one-line
prompt. Use a different model.

**The message arrives split into "(1/3)", "(2/3)"…**
Working as intended — Telegram caps messages at 4096 characters. Lower
`notice_items_per_category` for a shorter briefing.

**Nothing arrives at all**
Telegram may not be configured; that's a warning, not a failure. Check with
`python main.py --test-telegram` (see [06](06-telegram-setup.md)).

---

## Exercises

1. Add a fifth category to `feeds:` in `settings.yaml` and run `--run-once`.
2. Set `require_llm: true`, stop Ollama, and watch the failure alert arrive.
3. Set `lookback_hours: 6` and see how much the digest shrinks.
4. Change the schedule to `{"trigger": "interval", "minutes": 10}` to watch it
   fire repeatedly, then put it back.
