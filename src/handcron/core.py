import logging
from abc import ABC, abstractmethod
from datetime import date

from handcron.consumer.base import BaseConsumer
from handcron.consumer.process import ProcessConsumer
from handcron.consumer.simple import SimpleConsumer
from handcron.data import PathOrStr, PeriodicTask, TaskFn, TaskKey, WorkerType
from handcron.scheduler import Scheduler
from handcron.storage.base import BaseStorage
from handcron.storage.memory import MemoryStorage
from handcron.storage.sqlite import SqliteStorage

logger = logging.getLogger(__name__)


_DEFAULT_APP_NAME = "handcron"


class Handcron(ABC):
    """
    The main object, describing a crontab instance

    You can have different crontabs with the same backing storage.
    A consumer will only drain tasks from its respective crontab.

    This is an abstract class - pick a suitable subclass based
    on your storage needs.
    """
    def __init__(self, name: str = _DEFAULT_APP_NAME) -> None:
        self.name = name
        self.storage = self._make_storage()
        self.scheduler = Scheduler(self.storage)

    @abstractmethod
    def _make_storage(self) -> BaseStorage:
        raise NotImplementedError

    def periodic_task(
            self,
            cron: str,
            start_date: date | None = None,
            end_date: date | None = None,
            name: str | None = None,
    ):
        """Register a periodic task - see `PeriodicTask`"""
        def decorator(fn: TaskFn) -> TaskFn:
            name_ = name
            if name_ is None:
                name_ = fn.__qualname__

            self.scheduler.register_task(PeriodicTask(
                key=TaskKey(self.name, name_),
                fn=fn,
                cron=cron,
                start_date=start_date,
                end_date=end_date,
            ))
            return fn
        return decorator

    def create_consumer(self, worker_type: WorkerType = WorkerType.SIMPLE) -> BaseConsumer:
        """
        Create a `BaseConsumer` instance that can drain the queue

        Args:
            worker_type: Picks how should tasks be run; see `WorkerType`
        """
        match worker_type:
            case "simple":
                return SimpleConsumer(self)
            case "process":
                return ProcessConsumer(self)
            case _:
                raise NotImplementedError("bad worker type")


class MemoryHandcron(Handcron):
    """
    Handcron variant using in-memory ephemeral storage

    This is mostly suitable for tests and debugging,
    since you do not get consistent catchup semantics
    across restarts.

    See Also:
        `MemoryStorage`
    """
    def _make_storage(self) -> BaseStorage:
        return MemoryStorage(self)


class SqliteHandcron(Handcron):
    """
    Handcron variant using SQLite database storage

    See Also:
        `SqliteStorage`
    """
    def __init__(self, database: PathOrStr) -> None:
        self.database = database
        # call __init__ last, so that _make_storage() sees out attributes
        super().__init__()

    def _make_storage(self) -> BaseStorage:
        return SqliteStorage(self, database=self.database)


class PostgresHandcron(Handcron):
    """
    Handcron variant using PostgreSQL database storage

    See Also:
        `PostgresStorage`
    """

    def __init__(self, database: PathOrStr) -> None:
        self.database = database
        # call __init__ last, so that _make_storage() sees out attributes
        super().__init__()

    def _make_storage(self) -> BaseStorage:
        # local import, since the dependency is gated by "postgres" extra
        from handcron.storage.postgres import PostgresStorage
        return PostgresStorage(self, database=self.database)
