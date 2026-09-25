import logging
from datetime import date, datetime
from functools import partial
from uuid import uuid1

import pytest

from handcron import MemoryHandcron
from handcron.data import PeriodicTask, TaskKey, TaskRun, TaskRunStatus
from handcron.scheduler import Scheduler

# >>> calendar.prmonth(2026, 1)
#     January 2026
# Mo Tu We Th Fr Sa Su
#           1  2  3  4
#  5  6  7  8  9 10 11
# 12 13 14 15 16 17 18   <------
# 19 20 21 22 23 24 25
# 26 27 28 29 30 31
NOW = datetime(2026, 1, 15, 12, 0, 0)

@pytest.mark.parametrize(["cron", "start_date", "end_date", "last_run_date", "should_schedule"], [
    ["@daily", None, None, None, True],
    ["@daily", "2026-02-01", None, None, False],
    ["@daily", None, "2025-12-01", None, False],
    ["@weekly", None, None, None, True],
    ["@weekly", None, None, "2026-01-12", False],
    ["@weekly", None, None, "2026-01-10", True],
])
def test_scheduling_due_task(
        cron: str,
        start_date: str | None,
        end_date: str | None,
        last_run_date: str | None,
        should_schedule: bool
) -> None:
    task = PeriodicTask(
        TaskKey("test", "test"),
        lambda: None,
        cron,
        date.fromisoformat(start_date) if start_date is not None else None,
        date.fromisoformat(end_date) if end_date is not None else None,
    )

    if last_run_date is not None:
        tmp = date.fromisoformat(last_run_date)
        last_run_datetime = datetime(tmp.year, tmp.month, tmp.day)
    else:
        last_run_datetime = None

    last_run = TaskRun(
        key=TaskKey("test", "test"),
        id=uuid1(),
        status=TaskRunStatus.SUCCESS,
        time_scheduled=last_run_datetime,
        time_started=last_run_datetime,
        time_finished=last_run_datetime,
    ) if last_run_datetime is not None else None

    due_task = Scheduler.into_due_task(NOW, task, last_run)
    assert due_task is not None if should_schedule else due_task is None


def test_cron_validation():
    cron = MemoryHandcron()
    scheduler = cron.scheduler

    with pytest.raises(ValueError):
        scheduler.register_task(PeriodicTask(
            TaskKey(cron.name, "test"),
            lambda: None,
            "bad cron definition",
        ))


def test_callable_with_parameters(caplog):
    cron = MemoryHandcron()
    scheduler = cron.scheduler

    caplog.set_level(logging.WARNING)
    scheduler.register_task(PeriodicTask(
        TaskKey(cron.name, "test"),
        lambda foo: None,
        "@daily",
    ))
    assert "Callable for task test appears to have mandatory parameter foo without a default value" in caplog.text


def test_callable_without_name():
    cron = MemoryHandcron()

    cron.periodic_task("@daily", name="explicit_name")(partial(lambda foo: foo, "foo_value"))

    with pytest.raises(ValueError):
        cron.periodic_task("@daily")(partial(lambda foo: foo, "foo_value"))
