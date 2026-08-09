---
name: Bug report
about: Something in the lab isn't behaving. Full guide: agent-hub/study/12-reporting-a-bug-on-github.md
title: "<component> — <symptom>, <error string if there is one>"
labels: bug
---

## Environment

This repo runs one codebase on two very different machines, and the difference
between them is usually the bug. Fill this in even when it feels obvious.

| | |
|---|---|
| **Fails on** | macOS / Windows 11 — Python version — installed via python.org / Homebrew / system |
| **Works on** | the other machine? a previous commit? never worked? |
| **Component** | `agent-hub` (which task?) / docs / repo |
| **Commit** | output of `git rev-parse --short HEAD` |

## What I ran

```bash

```

## What happened

One line. "Completed successfully and produced 0 items" beats "it didn't work".

## What I expected

## Evidence

Paste text, not screenshots — in six months you'll search for the error string.
Trim to one representative failure plus the summary line.

```

```

<details>
<summary>Full log</summary>

```

```

</details>

## Already ruled out

The most useful section, and the one where you often spot the answer yourself.

- [ ] Not the network — because…
- [ ] Not the config — because…
- [ ] Not the code — because…

## Suspicion (optional)

A guess, clearly labelled as a guess. Delete if you don't have one.
