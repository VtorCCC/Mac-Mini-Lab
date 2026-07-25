# 03 · APScheduler & cron (when tasks run)

**APScheduler** ("Advanced Python Scheduler") is the library that runs your
tasks on a timer. agent-hub uses its `BlockingScheduler`, which means: start it,
and it takes over the process and runs forever, firing jobs at the right times.

## The `schedule` dict

Every task has a `schedule` — a plain Python dictionary describing *when* to
run. Example from `tasks/health_check.py`:

```python
schedule = {"trigger": "cron", "hour": 8, "minute": 0}
```

The `trigger` key picks the *style* of schedule. The other keys are options for
that style. agent-hub hands this dict straight to APScheduler, so anything
APScheduler supports works here.

## The two triggers you'll use most

### `cron` — "at specific clock times"

Like an alarm clock. You specify pieces of a time; unspecified pieces mean "any."

```python
{"trigger": "cron", "hour": 8, "minute": 0}                 # every day at 08:00
{"trigger": "cron", "hour": 9, "minute": 30}                # every day at 09:30
{"trigger": "cron", "minute": 0}                            # every hour, on the hour
{"trigger": "cron", "day_of_week": "mon", "hour": 7}        # Mondays at 07:00
{"trigger": "cron", "day_of_week": "mon-fri", "hour": 18}   # weekdays at 18:00
{"trigger": "cron", "day": 1, "hour": 0}                    # 1st of each month, midnight
```

Useful `cron` keys: `year, month, day, week, day_of_week, hour, minute, second`.
`day_of_week` accepts `mon tue wed thu fri sat sun` (or `0`–`6`).

### `interval` — "every N units"

Like an egg timer that restarts. Runs repeatedly with a fixed gap.

```python
{"trigger": "interval", "minutes": 30}   # every 30 minutes
{"trigger": "interval", "hours": 6}      # every 6 hours
{"trigger": "interval", "seconds": 45}   # every 45 seconds
```

Useful `interval` keys: `weeks, days, hours, minutes, seconds`.

## Changing a schedule without touching code

You can override any task's schedule in `settings.yaml`. This wins over the
default in the code:

```yaml
tasks:
  health_check:
    schedule:
      trigger: cron
      hour: 7          # moved the health check to 07:00
      minute: 15
```

Under the hood, `core/config.py`'s `task_schedule(...)` merges this override in,
and `core/scheduler.py`'s `register(...)` passes it to APScheduler.

## Timezones (important!)

`cron` times are interpreted in the timezone set at the top of `settings.yaml`:

```yaml
timezone: "America/New_York"
```

So `hour: 8` means 8 AM **in that timezone**. Set it to your Mac's actual
timezone or your "8:00" might fire at a surprising time. Leave it blank to use
the Mac's own local timezone. Names come from the
[tz database](https://en.wikipedia.org/wiki/List_of_tz_database_time_zones)
(e.g. `America/Los_Angeles`, `Europe/London`, `Asia/Tokyo`).

## How to *see* it work without waiting

You don't have to wait until 8:00 to test. Run a task immediately:

```bash
python main.py --run-once health_check
```

Or temporarily give a task a fast `interval` (say `seconds: 10`) in
`settings.yaml`, run `python main.py`, watch it fire a few times, then change it
back.

## Good to know

- **`max_instances=1`** (set in `register`): the same task won't run twice at
  once if one run is slow.
- **`misfire_grace_time=300`**: if the Mac was asleep and the job is up to 5
  minutes late, it still runs; later than that, that occurrence is skipped.
- The official docs are excellent:
  [APScheduler user guide](https://apscheduler.readthedocs.io/en/3.x/userguide.html).
