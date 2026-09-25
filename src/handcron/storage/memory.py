from types import TracebackType
from typing import TYPE_CHECKING

from handcron.data import TaskKey, TaskRun, TaskRunStatus
from handcron.storage.base import BaseStorage

if TYPE_CHECKING:
    from handcron.core import Handcron


class MemoryStorage(BaseStorage):
    """
    In-memory ephemeral storage

    This is mostly useful for debugging and testing.
    """
    def __init__(self, cron: "Handcron") -> None:
        super().__init__(cron)
        self._task_runs: list[TaskRun] = []

    def __exit__(
            self,
            exc_type: type[BaseException] | None,
            exc_val: BaseException | None,
            exc_tb: TracebackType | None
    ) -> None:
        pass

    def write_task_run(self, run: TaskRun) -> None:
        self._task_runs.append(run)

    def get_task_keys(self) -> list[TaskKey]:
        return list({run.key for run in self._task_runs})

    def flush(self) -> None:
        self._task_runs.clear()

    def get_last_task_runs(
            self,
            key: TaskKey,
            limit: int | None = None,
            status: TaskRunStatus | None = None
    ) -> list[TaskRun]:
        runs = self._get_task_runs_by_key(key)
        if status is not None:
            runs = [run for run in runs if run.status == status]
        runs.sort(key=lambda run: run.time_started, reverse=True)
        if limit is not None:
            if limit < 1:
                raise ValueError("limit must be a positive number")
            return runs[:limit]
        else:
            return runs

    def _get_task_runs_by_key(self, key: TaskKey) -> list[TaskRun]:
        return [run for run in self._task_runs if run.key == key]
