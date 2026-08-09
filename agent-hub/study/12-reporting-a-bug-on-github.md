# 12 – Reporting a bug on GitHub

You hit a real bug: `news_digest` ran on the Mac mini and produced nothing. This
guide is about the *other* half of that — writing it down so the problem is
findable, fixable, and not re-debugged from scratch in six months.

The worked example throughout is that exact bug.

---

## Where does it go? Four places, four jobs

This repo already has more than one place to write things down, which is
confusing until you see what each is *for*:

| Place | Answers | Lifetime |
|-------|---------|----------|
| **GitHub Issue** | "Something is wrong and it isn't fixed yet" | Open until closed |
| **Pull request** | "Here is the change that fixes it" | Merged, then history |
| [`WORKLOG.md`](../../WORKLOG.md) | "What happened on which day, and what we learned" | Append-only, forever |
| [`STATUS.md`](../../STATUS.md) | "What is true *right now*" | Overwritten constantly |

The rule of thumb: **an Issue is a question you can't answer yet.** Once you
know the answer, it becomes a PR. Once it's merged, the durable lesson goes in
the worklog and the current state goes in STATUS.

For a solo repo, it's tempting to skip Issues entirely and just fix things. The
reason not to: an Issue is where you write down the *evidence* while you still
have it. Two weeks later you will remember "the feeds broke" but not the exact
error string, which is the only part that's actually searchable.

---

## The anatomy of a report worth reading

Six sections. In this order, because it's the order a reader needs them.

### 1. Environment

Where it happened, and — critically — **where it doesn't**. Anyone who has
debugged for a living will tell you the single most valuable sentence in any bug
report is some form of:

> Works on machine A. Fails on machine B. Here is how they differ.

That one line collapsed our bug from "the internet is broken?" to "it's a macOS
certificate store thing" in one step. Always state the OS, the Python version,
and how Python was installed — python.org, Homebrew, and system Python behave
*differently* in ways that cause exactly this class of bug.

### 2. What you ran

The literal command. Copy-pasteable, no paraphrasing:

```bash
python main.py --run-once news_digest
```

### 3. What happened

The observable outcome in one line, then the evidence. "It didn't work" is not a
report. "It completed successfully and produced 0 items" is.

### 4. What you expected

Often obvious, occasionally not — and when it isn't, this is the whole bug. Say
it anyway; it's one line.

### 5. Evidence

Logs. But **trimmed**: the reader needs the shape of the failure, not 300
identical lines. Show one representative failure, the summary line, and the
count. Then hide the full dump behind a collapsible block so it's available
without burying everything else:

```markdown
<details>
<summary>Full log (13 feeds)</summary>

```
...paste here...
```

</details>
```

Two formatting notes that matter more than they sound:

- **Paste text, not screenshots**, whenever you can. Text is searchable. In six
  months you will search your own issues for `CERTIFICATE_VERIFY_FAILED` and be
  glad it's a string and not a PNG. Screenshots are a good *supplement* — they
  carry the terminal context — but never the only copy of an error message.
- **Wrap logs in triple backticks.** Unfenced logs get mangled by Markdown, and
  angle brackets like `<urlopen error ...>` can vanish entirely.

### 6. What you already ruled out

The most-skipped and most-valuable section. It stops the reader from suggesting
what you already tried, and it's usually where you notice the answer yourself.
For our bug:

- Not the network — the Telegram message sent fine in the same run.
- Not the feeds — the same URLs work from the Windows laptop.
- Not the code — the Windows machine runs the identical commit.

Writing those three lines *is* the diagnosis. Anything true on the Mac but not
on Windows is the culprit, and there's only one such thing: the certificates.

---

## The worked example

Here is the bug from this guide, written as an actual issue.

**Title:** `news_digest produces 0 items on macOS — SSL CERTIFICATE_VERIFY_FAILED on every feed`

A good title names the **symptom**, the **scope**, and the **error string**. Bad
titles: "news broken", "help", "doesn't work on Mac".

**Body:**

> **Environment**
> | | |
> |---|---|
> | Fails on | macOS (Mac mini), Python 3.11 |
> | Works on | Windows 11, Python 3.11, same commit |
> | Task | `news_digest` |
>
> **What I ran:** `python main.py --run-once news_digest`
>
> **What happened:** The task completed and reported `finished OK`, but built a
> digest of 0 items. All 13 feeds failed with the same SSL error.
>
> **What I expected:** A digest with items in it, as on Windows.
>
> **Evidence**
> ```
> WARNING | agent-hub.news.fetcher | feed returned no entries: https://hnrss.org/frontpage
>          (<urlopen error [SSL: CERTIFICATE_VERIFY_FAILED] unable to get local issuer certificate>)
> INFO    | agent-hub | Digest built: 0 items across 4 sections
> INFO    | agent-hub | News digest sent: 0 items, summarized=False
> ```
> …repeated for all 13 feeds across all 4 categories.
>
> **Already ruled out**
> - Not the network: the Telegram notification sent successfully in the same run.
> - Not the feed URLs: identical URLs work from the Windows machine.
> - Not the commit: both machines are on `f19579b`.
>
> **Suspicion:** Telegram goes through `requests` (which bundles its own CA
> certificates); feeds go through `feedparser` → `urllib` (which uses the system
> store). That's the only difference between the two paths.

That last paragraph is optional and worth writing when you have it. A suspicion
is not a diagnosis — label it as a guess so nobody treats it as fact — but it
gives the reader a place to start.

---

## Closing the loop

When the fix is ready, put `Fixes #12` in the pull request description. GitHub
links the two, and merging the PR **closes the issue automatically**. Use
`Fixes`, `Closes`, or `Resolves` — all three work. `See #12` links without
closing, which is what you want for a partial fix.

Then, per [the logging protocol](../../CLAUDE.md):

- Append the lesson to `WORKLOG.md` — not "fixed the SSL bug", but the durable
  part: *`requests` and `urllib` do not share a certificate store, so a
  cross-platform port can half-work while still logging success.*
- Reconcile `STATUS.md` with what's now true.

---

## A note on `gh`

The GitHub CLI would let you do all of this from the terminal:

```bash
gh issue create --title "..." --body-file issue.md
```

It is **not installed on the Windows dev machine**, so issues there get opened
through the web UI. On the Mac mini you can install it with
`brew install gh`, then `gh auth login`. Worth doing — `gh issue list` and
`gh pr create` remove most of the friction that makes people skip this process
entirely.

---

## Exercises

1. Write an issue for a bug you've already fixed. Notice which of the six
   sections you struggle to fill in — that's the one you habitually skip while
   debugging.
2. Open a real issue for the missing feed timeout *before* reading how it was
   fixed, then compare your report to the actual change.
3. Find a well-written issue in a large open-source project and map it onto the
   six sections above. Note what it does that this guide doesn't mention.
