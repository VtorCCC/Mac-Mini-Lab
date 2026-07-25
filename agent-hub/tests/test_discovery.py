"""Tests for task auto-discovery."""
from core.base_task import BaseTask
from core.scheduler import discover_task_classes


def test_health_check_is_discovered():
    classes = discover_task_classes()
    names = {cls.name for cls in classes}
    assert "health_check" in names


def test_only_real_task_subclasses_are_found():
    classes = discover_task_classes()
    # Everything discovered is a real BaseTask subclass (and not the base itself).
    assert classes  # at least one task exists
    assert all(issubclass(c, BaseTask) and c is not BaseTask for c in classes)
