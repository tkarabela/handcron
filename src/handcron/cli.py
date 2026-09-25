import logging
import os
import sys
from argparse import ArgumentParser
from datetime import datetime, timedelta
from time import sleep

from handcron import Handcron
from handcron.data import WorkerType

logger = logging.getLogger(__name__)


class CLI:
    def __init__(self) -> None:
        self.parser = ArgumentParser()
        self.parser.add_argument(
            "-k", "--worker-type", type=WorkerType, choices=[e.value for e in WorkerType],
            help="Worker type that should execute the tasks"
        )
        self.parser.add_argument(
            "-s", "--scheduler-interval", type=int,
            help="If provided, the scheduled will run periodically every `scheduler-interval` seconds - "
                 "this will create a long-running process, similar to traditional task queues. "
                 "By default, the scheduler only runs once at startup and then the program exits after all tasks are "
                 "executed."
        )
        self.parser.add_argument(
            "cron_dotted_path", metavar="my_module.cron",
            help="This specifies path from which to import your Handcron instance. "
                 "For example, if you have `my_module.py` with the line `cron = SqliteHandcron(...)`, "
                 "you should use `my_module.cron` as the parameter."
        )
        verbose_group = self.parser.add_mutually_exclusive_group()
        verbose_group.add_argument("-v", "--verbose", action="store_const", dest="logging_level", const=logging.DEBUG)
        verbose_group.add_argument("-q", "--quiet", action="store_const", dest="logging_level", const=logging.WARNING)

    def run(self, argv: list[str]) -> int:
        args = self.parser.parse_args(argv)
        worker_type: WorkerType = args.worker_type
        scheduler_interval: int | None = args.scheduler_interval
        cron_dotted_path: str = args.cron_dotted_path
        logging_level = args.logging_level if args.logging_level is not None else logging.INFO

        self.init_logging(logging_level)

        if scheduler_interval is not None and scheduler_interval <= 0:
            raise RuntimeError("scheduler_interval must be positive")

        cron = self.load_module_attribute(cron_dotted_path)
        if cron is None:
            return 1

        consumer = cron.create_consumer(worker_type)

        if scheduler_interval is None:
            logger.info("starting single consumer run")
            consumer.run()
        else:
            tick_delta = timedelta(seconds=scheduler_interval)
            logger.info("starting consumer run every %s", tick_delta)
            while True:
                tick = datetime.now()
                consumer.run()
                elapsed = datetime.now() - tick
                sleep_for_sec = (tick_delta - elapsed).total_seconds()
                if sleep_for_sec > 0:
                    sleep(sleep_for_sec)
        return 0

    @staticmethod
    def init_logging(level: int) -> None:
        main_logger = logging.getLogger("handcron")
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(levelname)-8s %(name)s: %(message)s"))
        main_logger.addHandler(handler)
        main_logger.setLevel(level)

    def load_module_attribute(self, dotted_path: str) -> Handcron | None:
        try:
            cron = self._load_module_attribute(dotted_path)
            if not isinstance(cron, Handcron):
                raise TypeError(f"{dotted_path} must be a Handcron instance")
            return cron
        except Exception:
            logger.exception(f"Failed to load {dotted_path}")
            return None

    def _load_module_attribute(self, dotted_path: str) -> Handcron:
        try:
            path, klass = dotted_path.rsplit(".", 1)
            __import__(path)
            mod = sys.modules[path]
            return getattr(mod, klass)
        except Exception:
            cwd = os.getcwd()
            if cwd not in sys.path:
                sys.path.insert(0, cwd)
                return self._load_module_attribute(dotted_path)
            else:
                raise
