"""Tests for the SQLite storage helper."""
from datetime import datetime, timezone

from core.storage import Storage


def test_count_runs_last_24h(tmp_path):
    # tmp_path is a fresh temporary folder pytest gives us for each test.
    storage = Storage(tmp_path / "test.db")
    storage.init_db()

    now = datetime.now(timezone.utc)
    storage.record_run("t1", now, now, "success")
    storage.record_run("t2", now, now, "error", "boom")

    assert storage.count_runs_last_24h() == 2


def test_empty_database_counts_zero(tmp_path):
    storage = Storage(tmp_path / "test.db")
    storage.init_db()
    assert storage.count_runs_last_24h() == 0
