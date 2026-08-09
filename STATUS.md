# Status

A living snapshot of the lab. **Overwrite this file in place** — it always
describes *now*, never history. History goes in [`WORKLOG.md`](WORKLOG.md).

_Last updated: 2026-08-09_

---

## At a glance

| Component | State | Deployed on the Mac mini? | Notes |
|-----------|-------|---------------------------|-------|
| `agent-hub` | 🟡 Built, running manually on the Mac | 🟡 Runs by hand, not via launchd | Code + tests + study guides complete. First manual runs done on the Mac mini. |
| ├ `health_check` | 🟡 Built, unverified | ❌ Not yet | Never run on a schedule for real. |
| └ `news_digest` | 🟡 Works on Windows; Mac fix pending re-test | 🟡 Ran, produced 0 items | SSL cert fix landed 2026-08-09 but is **not yet re-run on the Mac**. |
| _(docs)_ | 🟢 In place | n/a | `CLAUDE.md`, `STATUS.md`, `WORKLOG.md` |

Legend: 🟢 working · 🟡 built but unverified · 🔴 broken · ⚪ idea only

---

## agent-hub

**What it is:** one always-on Python process hosting scheduled tasks, kept alive
by `launchd`. See [`agent-hub/README.md`](agent-hub/README.md).

### Working

- Task auto-discovery from `tasks/`.
- Crash isolation — a failing task can't take down the process.
- SQLite run history in `data/agent-hub.db`.
- Rotating logs in `logs/`.
- CLI: `--list`, `--run-once`, `--test-telegram`.
- Config split: secrets in `config/.env`, behavior in `settings.yaml`.
- pytest suite covering the 24-hour run count, discovery, and crash isolation.
- Study guides `00`–`11` in `agent-hub/study/`.

### `news_digest` — ported from `NewsDocsObtainer`

Runs 07:00 daily: RSS across four categories → local LLM summaries →
`data/news/YYYY-MM-DD.md` → Telegram briefing.

Verified on the **Windows dev machine** (2026-08-02): a full `--run-once` run
fetched 35 items across 4 categories and summarized every one, no failures.
31 tests pass.

**First Mac mini run (2026-08-06) failed**: every feed returned
`SSL: CERTIFICATE_VERIFY_FAILED`, so the digest was built from 0 items — while
the Telegram message sent fine. Cause: `feedparser` fetches through `urllib`,
which uses the *system* certificate store, and a macOS python.org build leaves
that empty; `requests` (Telegram) bundles its own and was unaffected.
`services/news/fetcher.py` now passes urllib the certifi bundle explicitly, so
both paths behave the same everywhere. **Fixed and verified on Windows only —
still needs a Mac re-run to confirm.**

- Library lives in `agent-hub/services/news/`; `tasks/news_digest.py` is thin wiring.
- All knobs (model, feeds, lookback, output mode) live in `settings.yaml`.
- Degrades to headlines-without-summaries when Ollama is unreachable, rather
  than failing. `require_llm: true` flips that to a hard failure.
- Telegram briefing is chunked to respect the 4096-character cap.

### Not yet verified

Everything below has been *written* but never *run on the Mac mini*:

- [ ] Fresh install on the Mac mini (venv + `pip install -r requirements.txt`)
- [ ] Telegram bot created; `config/.env` filled in; `--test-telegram` succeeds
- [ ] `com.agenthub.scheduler.plist` paths edited for the real username/path
- [ ] `launchctl load` works and survives a reboot
- [ ] `health_check` fires on its own at 08:00 and the message arrives
- [ ] Timezone in `settings.yaml` matches the Mac's actual timezone

For `news_digest` specifically — the step-by-step version of this list is in
[`study/11-the-news-digest-task.md`](agent-hub/study/11-the-news-digest-task.md#verifying-this-on-the-mac-mini):

- [ ] `pip install -r requirements.txt` rerun (this task added five deps —
      `certifi` was added 2026-08-09), and `--list` shows `news_digest` as enabled
- [ ] **Feeds actually fetch** — the 0.5 step in guide 11. This is what failed on
      2026-08-06; confirm before touching anything LLM-related
- [x] `ollama list` shows a model — the Mac has `gemma3:latest` and `gemma4:12b`
- [ ] `ollama run <model>` actually responds (this is what caught `gemma4` on
      Windows — it crashed on a plain prompt)
- [ ] `model:` in `settings.yaml` set to that model. **Currently wrong on the
      Mac**: it reads `gemini4:12b`, which does not exist (`gemini` ≠ `gemma`).
      Should be `gemma3:latest`
- [ ] `--run-once news_digest` yields **0** "summarization failed" in the output
      file — i.e. `output_mode: native` works with that model
- [ ] The Telegram briefing arrives
- [ ] Ollama runs **as a service**, not just on login — verified by curling
      `/api/tags` after a reboot without logging in
- [ ] The 07:00 run fires on its own and the briefing arrives unprompted

### Known gaps / open questions

- `example_task` is still a disabled template.
- No log/DB retention policy — the SQLite run table grows without bound, and
  `data/news/` now gains one markdown file per day with nothing pruning it.
- No CI; tests run only when someone runs them locally.
- `news_digest` is unverified on macOS: the certificate fix is written and
  Windows-tested, but nobody has re-run it on the Mac yet.
- A task that fetches nothing still logs `finished OK`. That is technically
  correct — nothing crashed — but it is how the 2026-08-06 failure stayed quiet.
  Worth considering whether an empty digest should alert.
- The Mac's `settings.yaml` has drifted from the committed one (the `gemini4:12b`
  model name). No process yet for keeping per-machine config honest.

---

## Next up

1. **Re-run `news_digest` on the Mac mini** with the certifi fix and
   `model: gemma3:latest`. This is the immediate blocker.
2. Deploy `agent-hub` to the Mac mini properly and walk the "Not yet verified"
   list above.
3. Get Ollama running as a service there so the 07:00 run survives a reboot.
4. Revisit retention — both run history and `data/news/` — once there's real data.

---

## Ideas parked for later

- A second component in this lab (undecided).
- A way to see run history without opening SQLite by hand.
