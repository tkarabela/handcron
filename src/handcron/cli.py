"""
Handcron - lightweight Python library for periodic tasks
--------------------------------------------------------

For graceful shutdown, use SIGINT or SIGTERM on the main process.
This will stop after the currently in-flight tasks are finished.

"""
import argparse
import logging
import os
import sys
from argparse import ArgumentParser, Namespace
from datetime import datetime, timedelta
from enum import StrEnum
from time import sleep

from tabulate import tabulate

from handcron import Handcron
from handcron.data import TaskKey, TaskRun, TaskRunStatus, WorkerType

logger = logging.getLogger(__name__)


class Command(StrEnum):
    TICK = "tick"
    SERVE = "serve"
    ONESHOT = "oneshot"
    DESCRIBE = "describe"


class CLI:
    def __init__(self) -> None:
        self.parser = ArgumentParser(
            "handcron", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
        )
        verbose_group = self.parser.add_mutually_exclusive_group()
        verbose_group.add_argument(
            "-v", "--verbose", action="store_const", dest="logging_level", const=logging.DEBUG,
            help="print debug logs"
        )
        verbose_group.add_argument(
            "-q", "--quiet", action="store_const", dest="logging_level", const=logging.WARNING,
            help="print only warnings and errors"
        )

        subparsers = self.parser.add_subparsers(dest="command", metavar="command", required=True)

        tick_parser = subparsers.add_parser(
            Command.TICK,
            help="check for due tasks, run them and exit"
        )
        tick_parser.add_argument(
            "cron_dotted_path", metavar="my_module.cron",
            help="This specifies path from which to import your Handcron instance. "
                 "For example, if you have `my_module.py` with the line `cron = SqliteHandcron(...)`, "
                 "you should use `my_module.cron` as the parameter."
        )
        tick_parser.add_argument(
            "-k", "--worker-type", type=WorkerType, choices=[e.value for e in WorkerType], default=WorkerType.PROCESS,
            help="worker type that should execute the tasks"
        )

        serve_parser = subparsers.add_parser(
            Command.SERVE,
            help="periodically check for due tasks and run them"
        )
        serve_parser.add_argument(
            "cron_dotted_path", metavar="my_module.cron",
            help="This specifies path from which to import your Handcron instance. "
                 "For example, if you have `my_module.py` with the line `cron = SqliteHandcron(...)`, "
                 "you should use `my_module.cron` as the parameter."
        )
        serve_parser.add_argument(
            "-k", "--worker-type", type=WorkerType, choices=[e.value for e in WorkerType], default=WorkerType.PROCESS,
            help="worker type that should execute the tasks"
        )
        serve_parser.add_argument(
            "-s", "--scheduler-interval", type=int, default=60,
            help="time interval in seconds between scheduler ticks"
        )

        oneshot_parser = subparsers.add_parser(
            Command.ONESHOT,
            help="run a single task on demand"
        )
        oneshot_parser.add_argument(
            "cron_dotted_path", metavar="my_module.cron",
            help="This specifies path from which to import your Handcron instance. "
                 "For example, if you have `my_module.py` with the line `cron = SqliteHandcron(...)`, "
                 "you should use `my_module.cron` as the parameter."
        )
        oneshot_parser.add_argument(
            "task_name",
            help="name of task to run"
        )
        oneshot_parser.add_argument(
            "-k", "--worker-type", type=WorkerType, choices=[e.value for e in WorkerType], default=WorkerType.PROCESS,
            help="worker type that should execute the tasks"
        )

        describe_parser = subparsers.add_parser(
            Command.DESCRIBE,
            help="describe defined tasks and last run status"
        )
        describe_parser.add_argument(
            "cron_dotted_path", metavar="my_module.cron",
            help="This specifies path from which to import your Handcron instance. "
                 "For example, if you have `my_module.py` with the line `cron = SqliteHandcron(...)`, "
                 "you should use `my_module.cron` as the parameter."
        )
        describe_parser.add_argument(
            "--schedule-only", action="store_true", default=False,
            help="only print task schedule, do not connect to storage to query run status"
        )

    def run(self, argv: list[str]) -> int:
        args = self.parser.parse_args(argv)
        cron_dotted_path: str = args.cron_dotted_path
        logging_level = args.logging_level if args.logging_level is not None else logging.INFO
        command = Command(args.command)

        self.init_logging(logging_level)

        cron = self.load_module_attribute(cron_dotted_path)
        if cron is None:
            return 1

        match command:
            case Command.TICK:
                return self.run_tick(cron, args)
            case Command.SERVE:
                return self.run_serve(cron, args)
            case Command.ONESHOT:
                return self.run_oneshot(cron, args)
            case Command.DESCRIBE:
                return self.run_describe(cron, args)
            case _:
                raise NotImplementedError("bad commmand")

    def run_tick(self, cron: Handcron, args: Namespace) -> int:
        worker_type: WorkerType = args.worker_type
        cron.install_signal_handler()
        consumer = cron.create_consumer(worker_type)
        logger.info("starting single consumer run")
        consumer.run()
        return 0

    def run_serve(self, cron: Handcron, args: Namespace) -> int:
        worker_type: WorkerType = args.worker_type
        scheduler_interval: int = args.scheduler_interval
        cron.install_signal_handler()
        consumer = cron.create_consumer(worker_type)

        if scheduler_interval <= 0:
            logger.error("scheduler_interval must be positive")
            return 1

        tick_delta = timedelta(seconds=scheduler_interval)
        logger.info("starting consumer run every %s", tick_delta)
        while cron.running:
            tick = datetime.now()
            consumer.run()
            elapsed = datetime.now() - tick
            sleep_for_sec = (tick_delta - elapsed).total_seconds()
            if cron.running and sleep_for_sec > 0:
                sleep(sleep_for_sec)

        return 0

    def run_oneshot(self, cron: Handcron, args: Namespace) -> int:
        worker_type: WorkerType = args.worker_type
        task_name: str = args.task_name
        cron.install_signal_handler()

        try:
            task = cron.get_periodic_task(task_name)
        except KeyError:
            defined_task_names = [
                k.task_name
                for k in cron.scheduler.periodic_tasks
            ]
            logger.error("task %r is not defined (available tasks: %r)", task_name, defined_task_names)
            return 1

        consumer = cron.create_consumer(worker_type)
        logger.info("starting oneshot run (note: it will not be written to storage)")
        run = consumer.run_oneshot(task)
        return 0 if run.status == TaskRunStatus.SUCCESS else 1

    def run_describe(self, cron: Handcron, args: Namespace) -> int:
        schedule_only: bool = args.schedule_only

        table = []
        headers = ["task", "cron", "last run", "start_date", "end_date"]

        task_keys = list(cron.scheduler.periodic_tasks.keys())

        key_to_last_run: dict[TaskKey, TaskRun | None] = {}
        if not schedule_only:
            with cron.storage:
                for key in task_keys:
                    last_run = cron.storage.get_last_task_runs(key, limit=1)
                    key_to_last_run[key] = last_run[0] if last_run else None

        for key in task_keys:
            task = cron.get_periodic_task(key.task_name)
            last_run = key_to_last_run.get(key)
            table.append([
                task.key.task_name,
                task.cron,
                f"{last_run.status.name:8} {last_run.time_started:%Y-%m-%d %H:%M:%S}" if last_run else None,
                task.start_date,
                task.end_date
            ])

        logger.info(
            "Summary of instance %r:\n%s",
            cron.name,
            tabulate(table, headers, tablefmt="simple_outline")
        )
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
