# Status

A living snapshot of the lab. **Overwrite this file in place** — it always
describes *now*, never history. History goes in [`WORKLOG.md`](WORKLOG.md).

_Last updated: 2026-08-02_

---

## At a glance

| Component | State | Deployed on the Mac mini? | Notes |
|-----------|-------|---------------------------|-------|
| `agent-hub` | 🟡 Built, not yet deployed | ❌ Not yet | Code + tests + study guides complete. Never run on the actual Mac mini. |
| ├ `health_check` | 🟡 Built, unverified | ❌ Not yet | Never run on a schedule for real. |
| └ `news_digest` | 🟢 Verified on Windows | ❌ Not yet | Full run produces a real summarized digest. Needs Ollama on the Mac. |
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
28 tests pass.

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

- [ ] `pip install -r requirements.txt` rerun (this task added four deps), and
      `--list` shows `news_digest` as enabled
- [ ] `ollama list` shows a model, and `ollama run <model>` actually responds
      (this is what caught `gemma4` on Windows — it crashed on a plain prompt)
- [ ] `model:` in `settings.yaml` set to that model
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
- `news_digest` is unverified on macOS, and its model choice is unsettled: the
  Mac mini's available models are not known to match the dev machine's.

---

## Next up

1. Deploy `agent-hub` to the Mac mini and walk the "Not yet verified" list above.
2. Get Ollama running as a service there and pick the model for `news_digest`.
3. Revisit retention — both run history and `data/news/` — once there's real data.

---

## Ideas parked for later

- A second component in this lab (undecided).
- A way to see run history without opening SQLite by hand.
