from datetime import datetime
from types import TracebackType
from typing import TYPE_CHECKING, override
from uuid import UUID

import psycopg

from handcron.data import PathOrStr, TaskKey, TaskRun, TaskRunStatus
from handcron.storage.base import BaseStorage

if TYPE_CHECKING:
    from handcron.core import Handcron


# (id, cron_name, task_name, status, time_scheduled, time_started, time_finished)
_TaskRunRow = tuple[UUID, str, str, int, datetime, datetime, datetime]


class PostgresStorage(BaseStorage):
    """
    PostgreSQL database storage (using the ``psycopg3`` driver)
    """

    def __init__(self, cron: "Handcron", database: PathOrStr) -> None:
        super().__init__(cron)
        self.database = str(database)
        self._connection: psycopg.Connection | None = None

    @property
    def _conn(self) -> psycopg.Connection:
        if self._connection is None:
            raise RuntimeError("PostgresStorage must be used inside a `with` block")
        return self._connection

    def _create_schema(self) -> None:
        with self._conn.transaction():
            self._conn.execute("""
                CREATE TABLE IF NOT EXISTS handcron_task_run (
                    id UUID PRIMARY KEY,
                    cron_name TEXT NOT NULL,
                    task_name TEXT NOT NULL,
                    status SMALLINT NOT NULL,
                    time_scheduled TIMESTAMP NOT NULL,
                    time_started TIMESTAMP NOT NULL,
                    time_finished TIMESTAMP NOT NULL
                )
            """)
            self._conn.execute("""
                CREATE INDEX IF NOT EXISTS handcron_task_run_key_started
                ON handcron_task_run (cron_name, task_name, time_started)
            """)

    def flush(self) -> None:
        self._conn.execute("DELETE FROM handcron_task_run")

    def write_task_run(self, run: TaskRun) -> None:
        # connection is in autocommit mode, so each run is committed immediately
        self._conn.execute(
            """
            INSERT INTO handcron_task_run
            (id, cron_name, task_name, status, time_scheduled, time_started, time_finished)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (
                run.id,
                run.key.cron_name,
                run.key.task_name,
                int(run.status),
                run.time_scheduled,
                run.time_started,
                run.time_finished,
            ),
        )

    def get_task_keys(self) -> list[TaskKey]:
        rows = self._conn.execute(
            "SELECT DISTINCT cron_name, task_name FROM handcron_task_run ORDER BY cron_name, task_name"
        ).fetchall()
        return [TaskKey(cron_name, task_name) for cron_name, task_name in rows]

    def get_last_task_runs(self, key: TaskKey, limit: int | None = None, status: TaskRunStatus | None = None) -> list[
        TaskRun]:
        if limit is not None and limit < 1:
            raise ValueError("limit must be a positive number")

        # NULL status means "any status", and LIMIT NULL means no limit
        rows = self._conn.execute(
            """
            SELECT id, cron_name, task_name, status, time_scheduled, time_started, time_finished
            FROM handcron_task_run
            WHERE cron_name = %(cron_name)s
              AND task_name = %(task_name)s
              AND (%(status)s::smallint IS NULL OR status = %(status)s::smallint)
            ORDER BY time_started DESC
            LIMIT %(limit)s::bigint
            """,
            {
                "cron_name": key.cron_name,
                "task_name": key.task_name,
                "status": int(status) if status is not None else None,
                "limit": limit,
            },
        ).fetchall()
        return [self._row_to_task_run(row) for row in rows]

    @staticmethod
    def _row_to_task_run(row: _TaskRunRow) -> TaskRun:
        id_, cron_name, task_name, status, time_scheduled, time_started, time_finished = row
        return TaskRun(
            key=TaskKey(cron_name, task_name),
            id=id_,
            status=TaskRunStatus(status),
            time_scheduled=time_scheduled,
            time_started=time_started,
            time_finished=time_finished,
        )

    @override
    def __enter__(self) -> "BaseStorage":
        self._connection = psycopg.connect(self.database, autocommit=True)
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
