from abc import abstractmethod
from contextlib import AbstractContextManager
from typing import TYPE_CHECKING

from handcron.data import TaskKey, TaskRun, TaskRunStatus

if TYPE_CHECKING:
    from handcron.core import Handcron


class BaseStorage(AbstractContextManager["BaseStorage", None]):
    """
    Base class for persistent storage

    This class facilitates read/write to Handcron database.
    Connection to the underlying storage is handled via context manager.
    You must use `with` block to call any data access methods.
    """
    def __init__(self, cron: "Handcron") -> None:
        self.cron = cron

    @abstractmethod
    def flush(self) -> None:
        """Clear all data"""
        raise NotImplementedError

    @abstractmethod
    def write_task_run(self, run: TaskRun) -> None:
        """Append a task run into the database"""
        raise NotImplementedError

    @abstractmethod
    def get_task_keys(self) -> list[TaskKey]:
        """Get identifiers of task runs present in the database"""
        raise NotImplementedError

    @abstractmethod
    def get_last_task_runs(
            self,
            key: TaskKey,
            limit: int | None = None,
            status: TaskRunStatus | None = None
    ) -> list[TaskRun]:
        """
        Get `TaskRun` handles in descending order of `TaskRun.time_started`

        Args:
            key: Identifier of the task
            limit: By default, all results are returned; use a positive number
                here to limit the size of returned data.
            status: By default, task runs with any status are returned.
                Use a particular status here to filter the results.

        Returns:
            List of matching `TaskRun` instances
        """
        raise NotImplementedError

    def get_last_successful_task_run(self, key: TaskKey) -> TaskRun | None:
        """Return successful `TaskRun` with the latest `TaskRun.time_started`, or None"""
        match self.get_last_task_runs(key, limit=1, status=TaskRunStatus.DONE):
            case [run]:
                return run
            case []:
                return None
            case _:
                raise RuntimeError("logical error - expected one or zero last runs")
