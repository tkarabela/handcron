import logging
from datetime import datetime

from croniter import croniter

from handcron.data import DueTask, PeriodicTask, TaskKey, TaskRun
from handcron.storage.base import BaseStorage

logger = logging.getLogger(__name__)


class Scheduler:
    """This class keeps a registry of `PeriodicTask` objects and decides if they are due"""
    def __init__(self, storage: "BaseStorage") -> None:
        self.storage = storage
        self.periodic_tasks: dict[TaskKey, PeriodicTask] = {}

    def register_task(self, task: PeriodicTask) -> None:
        """
        Add a task to scheduler registry

        When adding a task with the same name multiple times,
        they are overwritten with a warning.
        """
        key = task.key
        if key in self.periodic_tasks:
            logger.warning("redefining previously declared periodic task %r", key.task_name)

        logger.debug("registering periodic task %r", key.task_name)
        self.periodic_tasks[key] = task

    def get_due_tasks(self, now: datetime | None = None) -> list[DueTask]:
        """
        Return a subset of registered tasks which are due now

        Args:
            now: Reference time, defaults to ``datetime.now()``

        Returns:
            List of `DueTask` objects
        """
        if now is None:
            now = datetime.now()

        output = []
        for task in self.periodic_tasks.values():
            last_run = self.storage.get_last_successful_task_run(task.key)
            due_task = self.into_due_task(now, task, last_run)
            if due_task is not None:
                output.append(due_task)
        return output

    @classmethod
    def into_due_task(cls, now: datetime, task: PeriodicTask, last_run: TaskRun | None) -> DueTask | None:
        """
        Decide if `PeriodicTask` is due or not

        Args:
            now: Reference time
            task: The task definition
            last_run: Most recent known successful run of the task, if any
        """
        before_now = croniter(task.cron, now).get_prev(ret_type=datetime)

        if last_run is not None:
            # We may have missed zero or more occurences - next time after last_time may be
            # too far in the past. We want to skip forward from that to last time before now
            # and record that as the scheduled time we are due for.
            last_time = last_run.time_started
            after_last_time = croniter(task.cron, last_time).get_next(ret_type=datetime)
            due_time = max(after_last_time, before_now)
            return cls._into_due_task_from_due_time(now, task, due_time)
        else:
            return cls._into_due_task_from_due_time(now, task, before_now)

    @classmethod
    def _into_due_task_from_due_time(cls, now: datetime, task: PeriodicTask, due_time: datetime) -> DueTask | None:
        if not cls._time_valid_for_task(due_time, task):
            logger.debug(
                "not scheduling task %r - due_time is not valid for this task (due_time=%s)",
                task.key.task_name, due_time
            )
            return None
        elif due_time > now:
            logger.debug(
                "not scheduling task %r - due_time is in the future (due_time=%s, now=%s)",
                task.key.task_name, due_time, now
            )
            return None
        else:
            logger.debug(
                "scheduling task %r - due_time is in the past (due_time=%s, now=%s)",
                task.key.task_name, due_time, now
            )
            return DueTask(task, due_time)

    @staticmethod
    def _time_valid_for_task(time: datetime, task: PeriodicTask) -> bool:
        if (start_date := task.start_date) is not None:
            if time.date() < start_date:
                return False
        elif (end_date := task.end_date) is not None:
            if time.date() > end_date:
                return False
        return True
