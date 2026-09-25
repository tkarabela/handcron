import os
from collections.abc import Iterator
from datetime import datetime, timedelta
from pathlib import Path
from uuid import uuid4

import pytest

from handcron import Handcron, MemoryHandcron, PostgresHandcron, SqliteHandcron
from handcron.data import TaskKey, TaskRun, TaskRunStatus
from handcron.storage.base import BaseStorage

POSTGRES_DSN_ENV = "HANDCRON_TEST_POSTGRES_DSN"

KEY_A = TaskKey("test", "a")
KEY_B = TaskKey("test", "b")
T0 = datetime(2026, 1, 15, 12, 0, 0, 123456)


def make_run(key: TaskKey, status: TaskRunStatus, hours: int) -> TaskRun:
    time = T0 + timedelta(hours=hours)
    return TaskRun(
        key=key,
        id=uuid4(),
        status=status,
        time_scheduled=time - timedelta(minutes=1),
        time_started=time,
        time_finished=time + timedelta(seconds=1, microseconds=654321),
    )


def make_cron(backend: str, tmp_path: Path) -> Handcron:
    match backend:
        case "memory":
            return MemoryHandcron()
        case "sqlite":
            return SqliteHandcron(tmp_path / "handcron.sqlite")
        case "postgres":
            dsn = os.environ.get(POSTGRES_DSN_ENV)
            if not dsn:
                pytest.skip(f"set {POSTGRES_DSN_ENV} to run PostgreSQL tests")
            return PostgresHandcron(dsn)
        case _:
            raise NotImplementedError("bad backend")


@pytest.fixture(params=["memory", "sqlite", "postgres"])
def cron(request: pytest.FixtureRequest, tmp_path: Path) -> Iterator[Handcron]:
    cron = make_cron(request.param, tmp_path)
    with cron.storage:
        cron.storage.flush()
    yield cron
    with cron.storage:
        cron.storage.flush()


@pytest.fixture
def storage(cron: Handcron) -> Iterator[BaseStorage]:
    with cron.storage:
        yield cron.storage


def test_empty(storage: BaseStorage) -> None:
    assert storage.get_task_keys() == []
    assert storage.get_last_task_runs(KEY_A) == []
    assert storage.get_last_successful_task_run(KEY_A) is None


def test_get_task_keys(storage: BaseStorage) -> None:
    storage.write_task_run(make_run(KEY_B, TaskRunStatus.DONE, 0))
    storage.write_task_run(make_run(KEY_A, TaskRunStatus.DONE, 1))
    storage.write_task_run(make_run(KEY_A, TaskRunStatus.FAILED, 2))
    assert sorted(storage.get_task_keys()) == [KEY_A, KEY_B]


def test_round_trip(storage: BaseStorage) -> None:
    run = make_run(KEY_A, TaskRunStatus.FAILED, 0)
    storage.write_task_run(run)
    assert storage.get_last_task_runs(KEY_A) == [run]


def test_last_task_runs_order_and_status(storage: BaseStorage) -> None:
    run0 = make_run(KEY_A, TaskRunStatus.DONE, 0)
    run1 = make_run(KEY_A, TaskRunStatus.FAILED, 1)
    run2 = make_run(KEY_A, TaskRunStatus.DONE, 2)
    other = make_run(KEY_B, TaskRunStatus.DONE, 3)
    for run in [run1, other, run0, run2]:
        storage.write_task_run(run)

    assert storage.get_last_task_runs(KEY_A) == [run2, run1, run0]
    assert storage.get_last_task_runs(KEY_A, status=TaskRunStatus.DONE) == [run2, run0]
    assert storage.get_last_task_runs(KEY_A, status=TaskRunStatus.FAILED) == [run1]


def test_last_task_runs_limit_returns_newest(storage: BaseStorage) -> None:
    runs = [make_run(KEY_A, TaskRunStatus.DONE, hours) for hours in range(5)]
    for run in runs:
        storage.write_task_run(run)

    assert storage.get_last_task_runs(KEY_A, limit=1) == [runs[4]]
    assert storage.get_last_task_runs(KEY_A, limit=2) == [runs[4], runs[3]]
    assert storage.get_last_task_runs(KEY_A, limit=10) == runs[::-1]


def test_last_task_runs_limit_with_status(storage: BaseStorage) -> None:
    done_old = make_run(KEY_A, TaskRunStatus.DONE, 0)
    done_new = make_run(KEY_A, TaskRunStatus.DONE, 1)
    failed = make_run(KEY_A, TaskRunStatus.FAILED, 2)
    for run in [done_old, done_new, failed]:
        storage.write_task_run(run)

    assert storage.get_last_task_runs(KEY_A, limit=1, status=TaskRunStatus.DONE) == [done_new]


@pytest.mark.parametrize("limit", [0, -1])
def test_last_task_runs_invalid_limit(storage: BaseStorage, limit: int) -> None:
    with pytest.raises(ValueError):
        storage.get_last_task_runs(KEY_A, limit=limit)


def test_last_successful_task_run(storage: BaseStorage) -> None:
    done = make_run(KEY_A, TaskRunStatus.DONE, 0)
    failed = make_run(KEY_A, TaskRunStatus.FAILED, 1)
    storage.write_task_run(done)
    storage.write_task_run(failed)

    assert storage.get_last_successful_task_run(KEY_A) == done
    assert storage.get_last_successful_task_run(KEY_B) is None


def test_flush(storage: BaseStorage) -> None:
    storage.write_task_run(make_run(KEY_A, TaskRunStatus.DONE, 0))
    storage.flush()
    assert storage.get_task_keys() == []
    assert storage.get_last_task_runs(KEY_A) == []


def test_persists_across_connections(cron: Handcron) -> None:
    run = make_run(KEY_A, TaskRunStatus.DONE, 0)
    with cron.storage:
        cron.storage.write_task_run(run)
    with cron.storage:
        assert cron.storage.get_last_task_runs(KEY_A) == [run]
