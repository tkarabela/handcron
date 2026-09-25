import sqlite3
from types import TracebackType
from typing import TYPE_CHECKING

from handcron.data import PathOrStr, TaskKey, TaskRunStatus, TaskRun
from handcron.storage.base import BaseStorage

if TYPE_CHECKING:
    from handcron.core import Handcron


class SqliteStorage(BaseStorage):
    """
    SQLite database storage (using the ``sqlite3`` driver from standard library)
    """

    def __init__(self, cron: "Handcron", database: PathOrStr) -> None:
        super().__init__(cron)
        self.database = str(database)

    # TODO

    def flush(self) -> None:
        pass  # TODO

    def write_task_run(self, run: TaskRun) -> None:
        pass  # TODO

    def get_task_keys(self) -> list[TaskKey]:
        pass  # TODO

    def get_last_task_runs(self, key: TaskKey, limit: int | None = None, status: TaskRunStatus | None = None) -> list[
        TaskRun]:
        pass  # TODO

    def __enter__(self) -> "BaseStorage":
        pass  # TODO
        return self

    def __exit__(
            self,
            exc_type: type[BaseException] | None,
            exc_val: BaseException | None,
            exc_tb: TracebackType | None
    ) -> None:
        pass  # TODO
