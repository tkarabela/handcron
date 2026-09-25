import sqlite3
from datetime import datetime
from types import TracebackType
from typing import TYPE_CHECKING, override
from uuid import UUID

from handcron.data import PathOrStr, TaskKey, TaskRun, TaskRunStatus
from handcron.storage.base import BaseStorage

if TYPE_CHECKING:
    from handcron.core import Handcron


_TABLE_NAME = "handcron_task_run"

# (id, cron_name, task_name, status, time_scheduled, time_started, time_finished)
_TaskRunRow = tuple[str, str, str, int, str, str, str]


class SqliteStorage(BaseStorage):
    """
    SQLite database storage (using the ``sqlite3`` driver from standard library)
    """

    def __init__(self, cron: "Handcron", database: PathOrStr) -> None:
        super().__init__(cron)
        self.database = str(database)
        self._connection: sqlite3.Connection | None = None

    @property
    def _conn(self) -> sqlite3.Connection:
        if self._connection is None:
            raise RuntimeError("SqliteStorage must be used inside a `with` block")
        return self._connection

    def _create_schema(self) -> None:
        with self._conn:
            self._conn.execute(f"""
                CREATE TABLE IF NOT EXISTS {_TABLE_NAME} (
                    id TEXT PRIMARY KEY,
                    cron_name TEXT NOT NULL,
                    task_name TEXT NOT NULL,
                    status INTEGER NOT NULL,
                    time_scheduled TEXT NOT NULL,
                    time_started TEXT NOT NULL,
                    time_finished TEXT NOT NULL
                )
            """)
            self._conn.execute(f"""
                CREATE INDEX IF NOT EXISTS {_TABLE_NAME}_key_started
                ON {_TABLE_NAME} (cron_name, task_name, time_started)
            """)

    def flush(self) -> None:
        with self._conn:
            self._conn.execute(f"DELETE FROM {_TABLE_NAME}")

    def write_task_run(self, run: TaskRun) -> None:
        # commit each run immediately, so that it survives a crash of subsequent tasks
        with self._conn:
            self._conn.execute(
                f"""
                INSERT INTO {_TABLE_NAME}
                (id, cron_name, task_name, status, time_scheduled, time_started, time_finished)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run.id.hex,
                    run.key.cron_name,
                    run.key.task_name,
                    int(run.status),
                    run.time_scheduled.isoformat(),
                    run.time_started.isoformat(),
                    run.time_finished.isoformat(),
                ),
            )

    def get_task_keys(self) -> list[TaskKey]:
        rows = self._conn.execute(
            f"SELECT DISTINCT cron_name, task_name FROM {_TABLE_NAME} ORDER BY cron_name, task_name"
        ).fetchall()
        return [TaskKey(cron_name, task_name) for cron_name, task_name in rows]

    def get_last_task_runs(self, key: TaskKey, limit: int | None = None, status: TaskRunStatus | None = None) -> list[
        TaskRun]:
        if limit is not None and limit < 1:
            raise ValueError("limit must be a positive number")

        query = f"""
            SELECT id, cron_name, task_name, status, time_scheduled, time_started, time_finished
            FROM {_TABLE_NAME}
            WHERE cron_name = ? AND task_name = ?
        """
        params: list[str | int] = [key.cron_name, key.task_name]
        if status is not None:
            query += " AND status = ?"
            params.append(int(status))
        query += " ORDER BY time_started DESC"
        if limit is not None:
            query += " LIMIT ?"
            params.append(limit)

        rows = self._conn.execute(query, params).fetchall()
        return [self._row_to_task_run(row) for row in rows]

    @staticmethod
    def _row_to_task_run(row: _TaskRunRow) -> TaskRun:
        id_, cron_name, task_name, status, time_scheduled, time_started, time_finished = row
        return TaskRun(
            key=TaskKey(cron_name, task_name),
            id=UUID(id_),
            status=TaskRunStatus(status),
            time_scheduled=datetime.fromisoformat(time_scheduled),
            time_started=datetime.fromisoformat(time_started),
            time_finished=datetime.fromisoformat(time_finished),
        )

    @override
    def __enter__(self) -> "BaseStorage":
        self._connection = sqlite3.connect(self.database)
        self._create_schema()
        return self

    @override
    def __exit__(
            self,
            exc_type: type[BaseException] | None,
            exc_val: BaseException | None,
            exc_tb: TracebackType | None
    ) -> None:
        if self._connection is not None:
            self._connection.close()
            self._connection = None
