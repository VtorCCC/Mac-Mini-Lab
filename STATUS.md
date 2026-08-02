# Status

A living snapshot of the lab. **Overwrite this file in place** — it always
describes *now*, never history. History goes in [`WORKLOG.md`](WORKLOG.md).

_Last updated: 2026-08-02_

---

## At a glance

| Component | State | Deployed on the Mac mini? | Notes |
|-----------|-------|---------------------------|-------|
| `agent-hub` | 🟡 Built, not yet deployed | ❌ Not yet | Code + tests + study guides complete. Never run on the actual Mac mini. |
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
- Study guides `00`–`10` in `agent-hub/study/`.

### Not yet verified

Everything below has been *written* but never *run on the Mac mini*:

- [ ] Fresh install on the Mac mini (venv + `pip install -r requirements.txt`)
- [ ] Telegram bot created; `config/.env` filled in; `--test-telegram` succeeds
- [ ] `com.agenthub.scheduler.plist` paths edited for the real username/path
- [ ] `launchctl load` works and survives a reboot
- [ ] `health_check` fires on its own at 08:00 and the message arrives
- [ ] Timezone in `settings.yaml` matches the Mac's actual timezone

### Known gaps / open questions

- Only one real task (`health_check`) exists; `example_task` is a disabled template.
- No log/DB retention policy — the SQLite run table grows without bound.
- No CI; tests run only when someone runs them locally.

---

## Next up

1. Deploy `agent-hub` to the Mac mini and walk the "Not yet verified" list above.
2. Decide the second real task — the first one that does something useful daily.
3. Revisit run-history retention once there's real data to look at.

---

## Ideas parked for later

- A second component in this lab (undecided).
- A way to see run history without opening SQLite by hand.
