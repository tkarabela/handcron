import os
import subprocess
import sys
from pathlib import Path

import pytest

from handcron.cli import CLI
from handcron.data import WorkerType

DATA_DIR = Path(__file__).resolve().parent.joinpath("data")


@pytest.mark.parametrize("cron", ["demo_memory.cron", "demo_sqlite.cron"])
@pytest.mark.parametrize("worker", [WorkerType.SIMPLE, WorkerType.PROCESS])
def test_demo_by_running_module(worker: WorkerType, cron: str):
    cmd = [
        sys.executable,
        "-m",
        "handcron",
        "tick",
        "--worker",
        worker.value,
        cron,
    ]
    subprocess.run(cmd, check=True, timeout=30, cwd=DATA_DIR)


@pytest.mark.timeout(30)
@pytest.mark.parametrize("cron", ["demo_memory.cron", "demo_sqlite.cron"])
@pytest.mark.parametrize("worker", [WorkerType.SIMPLE, WorkerType.PROCESS])
def test_demo_by_invoking_cli_from_python(worker: WorkerType, cron: str):
    cmd = [
        "tick",
        "--worker",
        worker.value,
        cron,
    ]
    old_cwd = os.getcwd()
    try:
        os.chdir(DATA_DIR)
        assert CLI().run(cmd) == 0
    finally:
        os.chdir(old_cwd)
