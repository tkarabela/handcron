import subprocess
import sys
from pathlib import Path

import pytest

from handcron.data import WorkerType

DATA_DIR = Path(__file__).resolve().parent.joinpath("data")


@pytest.mark.parametrize("cron", ["demo_memory.cron", "demo_sqlite.cron"])
@pytest.mark.parametrize("worker", [WorkerType.SIMPLE, WorkerType.PROCESS])
def test_demo_memory(worker: WorkerType, cron: str):
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
