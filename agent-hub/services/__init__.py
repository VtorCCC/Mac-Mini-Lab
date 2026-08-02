"""Reusable libraries that tasks build on.

Why this folder exists, and why the code isn't in ``tasks/``:

``core/scheduler.py`` auto-discovers tasks by **importing every module inside
tasks/** at startup. Keeping that folder to one small task class per file makes
discovery fast and unambiguous. Anything bigger — a multi-file library like the
news digest — lives here instead, and the task file just calls into it.
"""
