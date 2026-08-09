# Worklog

Dated record of work in this repo. **Newest entry first. Append only** — never
edit a past entry; if something turned out to be wrong, say so in a new one.

For the *current* state of things, see [`STATUS.md`](STATUS.md).

<details>
<summary><strong>Entry template</strong> (copy this)</summary>

```markdown
## YYYY-MM-DD — Short title

**Who:** Vic / Claude / both
**Component:** agent-hub · docs · repo

**Done**
- What actually changed, in plain language.

**Decisions**
- Choice made, and why. Skip the section if there were none.

**Learned / gotchas**
- Anything that would waste time again if forgotten.

**Next**
- The obvious next step for whoever picks this up.
```

</details>

---

## 2026-08-09 — Fix `news_digest` fetching nothing on the Mac mini (SSL certs)

**Who:** both
**Component:** agent-hub · docs

**Done**
- Diagnosed the first real Mac mini run of `news_digest` (2026-08-06), which
  reported `finished OK` but built a digest from **0 items**. Every one of the
  13 feeds had failed with `SSL: CERTIFICATE_VERIFY_FAILED`.
- `services/news/fetcher.py` now builds an `ssl` context from the certifi bundle
  and hands it to feedparser via an explicit `HTTPSHandler`.
- Added the fetch timeout that was missing entirely (`_FEED_TIMEOUT_SECONDS`,
  15s), applied via the global default socket timeout and restored in a
  `finally` so no other task inherits it.
- `certifi` promoted to a declared dependency in `requirements.txt` — it was
  already installed, but only as a transitive dependency of `requests`.
- Three tests added (31 total): the handler is certifi-backed, the timeout is
  applied, and the timeout is restored *even when the fetch raises*.
- Guide 11: new `CERTIFICATE_VERIFY_FAILED` troubleshooting entry, a "0.5 — can
  it reach the feeds at all?" step ahead of the Ollama steps, and a note that
  `gemini` and `gemma` are one letter apart.
- New `study/12-reporting-a-bug-on-github.md` — how to write this class of bug
  up as an issue, using this bug as the worked example. Indexed in the README
  and `00-start-here.md`.
- Added `.github/ISSUE_TEMPLATE/bug_report.md`, whose Environment block asks
  which machine it fails on *and* which it works on.
- Gitignored `agent-hub/study/.obsidian/` — per-machine editor UI state.

**Decisions**
- **Fixed it in code rather than only on the Mac.** Running macOS's
  `Install Certificates.command` would have unblocked things in one command, but
  the fix would live on one machine and silently not exist on the next one. The
  code change makes feed fetching behave the same everywhere, which is the whole
  point of a repo that targets two operating systems.
- **Kept the timeout as a module constant, not a `settings.yaml` option.** No
  evidence yet that it needs to differ per machine; promoting it later is easy.
- Left the `finished OK`-on-empty-digest behaviour alone for now and logged it
  in STATUS as an open question, rather than widening this change.

**Learned / gotchas**
- **`requests` and `urllib` do not share a certificate store.** `requests` ships
  certifi and points OpenSSL at it; `urllib` asks for the system default. On
  Windows that reads the OS cert store and works, on a macOS python.org build it
  reads an empty directory. So a cross-platform port can half-work — Telegram
  delivering perfectly while every feed fails, in the same run, on the same
  network. That contrast *was* the diagnosis.
- **feedparser never raises on a network error.** It converts the `URLError`
  into `bozo_exception` and returns an empty result, so the `try/except` around
  `parse()` never fires. The failure surfaces only as a per-feed warning, and
  the run is honestly reported as successful.
- A task can be green and useless at the same time. "Did it crash?" and "did it
  do anything?" are different questions.
- The Mac's `settings.yaml` had `model: "gemini4:12b"` — a model that does not
  exist anywhere (`gemini` is Google's hosted one; `gemma` is the pullable one).
  Independent of the SSL bug, and it would still have produced headline-only
  output after the certs were fixed.

**Next**
- Vic re-runs `--run-once news_digest` on the Mac mini after `pip install -r
  requirements.txt` and setting `model: gemma3:latest`. **Everything macOS here
  is unverified** — the fix was only proven on Windows (real feed fetched, 121
  CAs loaded, 31 tests green).
- If it works, that clears the way for the launchd deployment.

---

## 2026-08-02 — Port NewsDocsObtainer in as the `news_digest` task

**Who:** both
**Component:** agent-hub

**Done**
- Ported the standalone `NewsDocsObtainer` CLI (RSS → local LLM summaries →
  dated markdown) into agent-hub as the `news_digest` task, running 07:00 daily
  and pushing a briefing to Telegram.
- New `services/` package for libraries too big to live in a task file;
  the news code sits in `services/news/` and `tasks/news_digest.py` is ~40 lines
  of wiring.
- Added `core.config.task_options()` so any task can keep arbitrary settings in
  an `options:` block. Only addition to `core/`.
- Feeds, model, lookback, caps and output mode all moved into `settings.yaml`.
- Added `study/11-the-news-digest-task.md`; updated the README and study index.
- 16 new tests (28 total, all passing).

**Decisions**
- **Library in `services/`, not `tasks/`.** The scheduler imports every module
  in `tasks/` to discover them, so that folder stays one small class per file.
- **Imports inside `run()`.** A top-level `import feedparser` in a task file
  would mean one missing optional dependency stops agent-hub from starting *at
  all*. Inside `run()`, the blast radius is one failed task.
- **`sys.exit()` had to go.** The original CLI exited with code 2 when Ollama
  was down. `SystemExit` derives from `BaseException`, so it would slip past the
  `except Exception` guard in `core/scheduler.py` and kill the whole process.
  Everything now raises `OllamaUnavailableError`. There's a test pinning this.
- **Degrade instead of fail.** No Ollama → headlines without summaries, clearly
  flagged, rather than no digest. `require_llm: true` opts back into failing.
- **Telegram briefing is a summary, not the whole digest** (top 3 per category
  + link to the file), chunked to respect the 4096-character cap.

**Learned / gotchas**
- **pydantic-ai defaults to tool calling for structured output, and `gemma3`
  has no tool support.** First real run produced "(summarization failed)" for
  every category. Fix: `output_mode: native`, which uses Ollama's JSON-schema
  constrained output instead. Measured on 2026-08-02:

  | mode | gemma3:latest | gpt-oss:20b |
  |------|---------------|-------------|
  | native | works | works |
  | tool | 400 "does not support tools" | works |
  | prompted | exceeded output retries | works |

- **`gemma4:latest` and `gemma4:e4b` both crash llama-server on this Windows
  machine** (`exit status 0xc0000409`, stack buffer overrun) — even on a plain
  one-line prompt with no pydantic-ai involved. Not our bug, but it rules out
  the original project's default model here. Default is now `gemma3:latest`.
- The inherited `pydantic-ai-slim<1.0` pin now resolves to 0.8.1, which imports
  `opentelemetry._events` — removed in current opentelemetry-api, so it fails at
  import. Repinned to `>=2.0,<3`.
- Markdown blockquotes need `> ` on *every* line. LLM output is routinely
  multi-paragraph, so `f"> {summary}"` left most of the synthesis outside the
  quote. Fixed in the writer, with a test.
- A full run takes 2–5 minutes (five LLM calls against a local model).

**Next**
- Deploy to the Mac mini and work through the 7-step verification checklist in
  `study/11-the-news-digest-task.md`. The two things that genuinely have to be
  re-proven there are the **model** and the **output mode** — both depend on
  what Ollama has on that machine.
- Ollama must run **as a service** there, not just on login, or it won't be up
  when the task fires at 07:00.
- Nothing prunes `data/news/` — one file per day accumulates forever.

---

## 2026-08-02 — Add CLAUDE.md and the status/worklog system

**Who:** both
**Component:** docs

**Done**
- Added `CLAUDE.md` at the repo root: repo purpose, component map, the
  Windows-dev / macOS-deploy split, commands, code conventions, and the logging
  protocol below.
- Added `STATUS.md` — the living snapshot of what works and what's unverified.
- Added `WORKLOG.md` (this file) with an entry template.
- Backfilled entries for the work already in git history.

**Decisions**
- **Two files, not one.** `STATUS.md` gets overwritten and answers "where are we
  now?"; `WORKLOG.md` is append-only and answers "how did we get here?" Mixing
  the two makes both harder to skim.
- **Root-level, not `docs/`.** Small personal repo — discoverability beats tidiness.
- Recorded agent-hub's load-bearing invariants (crash isolation, auto-discovery,
  config-over-code, APScheduler pinned to 3.x) in `CLAUDE.md` so future changes
  don't quietly undo them.

**Learned / gotchas**
- `gh` is not installed on the Windows dev machine — pull requests have to go
  through the GitHub web UI.

**Next**
- Deploy `agent-hub` to the Mac mini and work through the unverified checklist
  in `STATUS.md`.

---

## 2026-07-25 — Merge agent-hub into `main`

**Who:** Vic
**Component:** agent-hub

**Done**
- Merged PR #1 (`claude/agent-hub-scheduled-tasks-iwvgx3`) into `main`.
- Updated the root `README.md`.

**Next**
- Get it running on the actual Mac mini.

---

## 2026-07-21 — Build agent-hub

**Who:** both
**Component:** agent-hub

**Done**
- Built the APScheduler-based scheduled-task host: auto-discovery, crash
  isolation, SQLite run history, rotating logs, Telegram notifier, and a
  `launchd` plist for 24/7 operation.
- Shipped one real task (`health_check`, daily at 08:00) and a disabled
  `example_task` template.
- Added a pytest suite and the `study/` guides (`00`–`10`).

**Decisions**
- One process hosting many tasks, rather than one cron entry per job — easier to
  keep alive, log, and reason about.
- Schedules live in `settings.yaml`, not in code, so changing a time needs no
  Python edit.
- Pinned APScheduler to the 3.x series; 4.x is a rewrite with a different API.

**Next**
- Deploy to the Mac mini; verify launchd survives a reboot.

---

## 2026-07-20 — Initial commit

**Who:** Vic
**Component:** repo

**Done**
- Created the repo as a place to study Claude Code + GitHub and to store drafts.
