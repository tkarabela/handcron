import logging
import multiprocessing
import sys
from uuid import UUID

from handcron.consumer.base import BaseSerialConsumer
from handcron.data import DueTask, TaskFn, TaskRunStatus

logger = logging.getLogger(__name__)


class ProcessConsumer(BaseSerialConsumer):
    """
    Serial consumer implementation that spawns a new subprocess per task

    This is not very efficient, but it is robust in face of process crashes.
    """
    def _execute_task_fn(self, due_task: DueTask, run_id: UUID) -> TaskRunStatus:
        p = multiprocessing.Process(target=ProcessConsumer._execute_task_fn_inner, args=(due_task.task.fn,))
        p.start()
        p.join()
        if p.exitcode != 0:
            logger.error("task run %s (%s) process exited with code %r", due_task.task.key, run_id.hex, p.exitcode)
            return TaskRunStatus.FAILURE
        else:
            return TaskRunStatus.SUCCESS

    @staticmethod
    def _execute_task_fn_inner(fn: TaskFn) -> None:
        try:
            fn()
        except Exception:
            logger.exception("task failed with exception")
            sys.exit(1)
