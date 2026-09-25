import logging
from uuid import UUID

from handcron.consumer.base import BaseSerialConsumer
from handcron.data import DueTask, TaskRunStatus

logger = logging.getLogger(__name__)


class SimpleConsumer(BaseSerialConsumer):
    """
    The simplest serial consumer implementation, just runs the tasks from the main thread

    This is not a robust strategy, since if any task crashes the process,
    it takes down all the enqueued tasks down as well. Handy for debugging
    since there is no additional threads or processes.
    """
    def _execute_task_fn(self, due_task: DueTask, run_id: UUID) -> TaskRunStatus:
        try:
            due_task.task.fn()
            return TaskRunStatus.DONE
        except Exception:
            logger.exception("task failed with exception")
            return TaskRunStatus.FAILED
