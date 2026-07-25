# 07 · launchd & the Mac (running 24/7)

For agent-hub to fire tasks at 8:00 every day, it has to be **running** at 8:00
every day. You could leave a terminal open forever — but the proper macOS way is
`launchd`.

## What is launchd?

`launchd` is the service manager built into macOS. It starts programs, keeps
them running, and restarts them if they crash or the Mac reboots. You describe
the job in a small XML file called a **plist** ("property list"). Ours is
`com.agenthub.scheduler.plist`.

## What our plist says

Open `com.agenthub.scheduler.plist` — each part is commented. The important keys:

| Key | Meaning |
|-----|---------|
| `Label` | A unique name: `com.agenthub.scheduler` |
| `ProgramArguments` | Which Python to run, and that it should run `main.py` |
| `WorkingDirectory` | The agent-hub folder |
| `KeepAlive` `true` | **Restart the process whenever it exits** (crash, reboot, anything) |
| `RunAtLoad` `true` | Start immediately when loaded, and at login |
| `StandardOutPath` / `StandardErrorPath` | Where console output is saved |

`KeepAlive` is what makes it truly always-on: if the process dies for any
reason, launchd brings it right back.

## Install it (one-time)

**1. Edit the paths.** Replace every `YOUR_USERNAME` in the plist with your Mac
username (run `whoami` if unsure), and adjust the folder if agent-hub lives
somewhere other than `/Users/YOUR_USERNAME/agent-hub`. The plist points at
`.venv/bin/python3`, so make sure you created the virtualenv first
(`python3 -m venv .venv && pip install -r requirements.txt`).

**2. Copy it to your LaunchAgents folder:**

```bash
cp com.agenthub.scheduler.plist ~/Library/LaunchAgents/
```

`~/Library/LaunchAgents/` is where per-user launchd jobs live.

**3. Load (and thereby start) it:**

```bash
launchctl load ~/Library/LaunchAgents/com.agenthub.scheduler.plist
```

## Everyday commands

```bash
# Is it running? A number (PID) in the first column = yes.
launchctl list | grep agenthub

# Watch the app's log live
tail -f logs/agent-hub.log

# Stop it
launchctl unload ~/Library/LaunchAgents/com.agenthub.scheduler.plist

# Start it again (e.g. after editing code or settings)
launchctl load ~/Library/LaunchAgents/com.agenthub.scheduler.plist
```

Whenever you change code or `settings.yaml`, do an **unload then load** so the
service restarts with your changes.

## Where to look when something's wrong

1. `logs/agent-hub.log` — the app's own diary (most useful).
2. `logs/launchd.err.log` — captures startup errors (e.g. "python: no such
   file"), which usually mean a wrong path in the plist.
3. `launchctl list | grep agenthub` — the number just left of the label is the
   **last exit code**. `0` is clean; anything else means it exited with an error
   (check the logs).

## Common gotchas

- **Wrong paths.** The #1 issue. The plist needs *absolute* paths, and
  `YOUR_USERNAME` must be replaced. Check `logs/launchd.err.log`.
- **Forgot the venv.** The plist runs `.venv/bin/python3`; if you never created
  the venv, that file doesn't exist. Create it and `pip install -r requirements.txt`.
- **It keeps restarting fast.** If the program crashes immediately on startup,
  `KeepAlive` will restart it in a loop. Read `logs/launchd.err.log`, fix the
  cause, then unload/load.
- **Editing the plist after loading.** Always `unload` before `load` again;
  loading twice without unloading does nothing.

## Uninstalling

```bash
launchctl unload ~/Library/LaunchAgents/com.agenthub.scheduler.plist
rm ~/Library/LaunchAgents/com.agenthub.scheduler.plist
```

## Note for modern macOS

Newer macOS versions also offer `launchctl bootstrap`/`bootout` as replacements
for `load`/`unload`. The `load`/`unload` commands shown here still work well for
a personal LaunchAgent like this one, so start with them.
