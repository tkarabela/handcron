import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from handcron.data import DueTask, PeriodicTask, TaskRun, TaskRunStatus

if TYPE_CHECKING:
    from handcron.core import Handcron


logger = logging.getLogger(__name__)


class BaseConsumer(ABC):
    """Base class for a consumer that processes due tasks"""
    def __init__(self, cron: "Handcron") -> None:
        self.cron = cron

    def run(self) -> None:
        """Query the scheduler and run all tasks that are due currently, then return"""
        logger.debug("connecting to storage")
        with self.cron.storage:
            logger.debug("starting consumer run")
            self._run()
            logger.debug("finished consumer run")
        logger.debug("torn down storage")

    @abstractmethod
    def run_oneshot(self, task: PeriodicTask) -> TaskRun:
        """Run a single task without writing to the database"""
        raise NotImplementedError

    @abstractmethod
    def _run(self) -> None:
        """Implement this in your subclass"""
        raise NotImplementedError

    def log_run_start(self, due_task: DueTask, run_id: UUID) -> None:
        """Call this before running a task"""
        logger.info("task run %s (%s) started", due_task.task.key, run_id.hex)

    def log_run_end(self, run: TaskRun, write_to_storage: bool = True) -> None:
        """Call this after running a task"""
        match run.status:
            case TaskRunStatus.SUCCESS:
                logger.info("task run %s (%s) finished", run.key, run.id.hex)
            case TaskRunStatus.FAILURE:
                logger.error("task run %s (%s) failed", run.key, run.id.hex)
            case _:
                raise NotImplementedError("bad task run status type")

        if write_to_storage:
            self.cron.storage.write_task_run(run)

    def generate_run_id(self) -> UUID:
        """Run this to generate an ID for a new task run"""
        return uuid4()


class BaseSerialConsumer(BaseConsumer, ABC):
    """Base class for simple, serial consumers (just iterate over `Scheduler.get_due_tasks()`)"""
    def _run(self) -> None:
        due_tasks = self.cron.scheduler.get_due_tasks()
        for due_task in due_tasks:
            self._run_due_task(due_task)

    def run_oneshot(self, task: PeriodicTask) -> TaskRun:
        return self._run_due_task(
            due_task=DueTask(
                task=task,
                time_scheduled=datetime.now()
            ),
            write_to_storage=False,
        )

    def _run_due_task(self, due_task: DueTask, write_to_storage: bool = True) -> TaskRun:
        run_id = self.generate_run_id()
        time_started = datetime.now()
        self.log_run_start(due_task, run_id)

        status = self._execute_task_fn(due_task, run_id)
        run = TaskRun(
            key=due_task.task.key,
            id=run_id,
            status=status,
            time_scheduled=due_task.time_scheduled,
            time_started=time_started,
            time_finished=datetime.now(),
        )
        self.log_run_end(run, write_to_storage)
        return run

    @abstractmethod
    def _execute_task_fn(self, due_task: DueTask, run_id: UUID) -> TaskRunStatus:
        """Implement this in your subclass"""
        raise NotImplementedError
