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
