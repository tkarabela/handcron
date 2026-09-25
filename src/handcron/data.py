import os
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime
from enum import IntEnum, StrEnum
from uuid import UUID

PathOrStr = str | os.PathLike[str]


class TaskRunStatus(IntEnum):
    """
    Status of a `TaskRun`

    Attributes:
        DONE: The task finished successfully
        FAILED: The task did not finish correctly

    """
    DONE = 0
    FAILED = 1


@dataclass(frozen=True, order=True)
class TaskKey:
    """
    Qualified `PeriodicTask` name

    Attributes:
        cron_name: Name of `Handcron` instance the task belongs to
        task_name: Name of the task (typically this is name of the task callable)
    """
    cron_name: str
    task_name: str

    def __str__(self) -> str:
        return f"{self.cron_name}.{self.task_name}"


@dataclass(frozen=True)
class TaskRun:
    """
    Structure describing a past run of a given `PeriodicTask`

    Attributes:
        key: Name of the `PeriodicTask`
        id: Unique identifier of this run
        status: Whether the task finished successfully or not
        time_scheduled: Time when this run was due (if there were multiple
            missed runs, this relates to the most recent one)
        time_started: Time when the task started execution
        time_finished: Time when the task finished execution

    """
    key: TaskKey
    id: UUID
    status: TaskRunStatus
    time_scheduled: datetime
    time_started: datetime
    time_finished: datetime


TaskFn = Callable[[], None]


@dataclass(frozen=True)
class PeriodicTask:
    """
    Structure describing schedule on which a named task is run

    Attributes:
        key: Name of the task
        fn: Callable of the task (must not take any parameters;
            any return value is ignored)
        cron: Schedule definition per the ``croniter`` library
            (eg. ``"@daily"`` or ``"0 */2 * * *"`` - every two hours).
        start_date: If given, the task must not run earlier than this date.
        end_date: If given, the task must not run after this date.

    """
    key: TaskKey
    fn: TaskFn
    cron: str
    start_date: date | None
    end_date: date | None


@dataclass(frozen=True)
class DueTask:
    """
    Structure describing the scheduler output

    Attributes:
        task: The task being scheduled
        time_scheduled: Time at which this task was due

    """
    task: PeriodicTask
    time_scheduled: datetime


class WorkerType(StrEnum):
    """
    Kind of worker that should execute the tasks

    Attributes:
        SIMPLE: `SimpleConsumer`
        PROCESS: `ProcessConsumer`
    """
    SIMPLE = "simple"
    PROCESS = "process"
