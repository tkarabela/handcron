[![handcron build master branch](https://img.shields.io/github/actions/workflow/status/tkarabela/handcron/ci.yml?branch=master)](https://github.com/tkarabela/handcron/actions)
[![handcron test code coverage](https://img.shields.io/codecov/c/github/tkarabela/handcron)](https://app.codecov.io/github/tkarabela/handcron)
[![Static Badge](https://img.shields.io/badge/Pyrefly%20%26%20Ruff-checked-blue?style=flat)](https://github.com/tkarabela/handcron/actions)
[![PyPI - Version](https://img.shields.io/pypi/v/handcron.svg?style=flat)](https://pypi.org/project/handcron/)
[![PyPI - Status](https://img.shields.io/pypi/status/handcron.svg?style=flat)](https://pypi.org/project/handcron/)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/handcron.svg?style=flat)](https://pypi.org/project/handcron/)
[![PyPI - License](https://img.shields.io/pypi/l/handcron.svg?style=flat)](LICENSE.txt)

# 🕐 handcron 💁

_Python task queue with manual ticks_

Unlike a traditional task queue, _handcron_ is designed to process
due tasks and then stop - by default, there is no long-running process in the background. 
Instead, you periodically run `handcron tick` yourself (from a cron, etc.).

It is similar to [django-cron](https://github.com/Tivix/django-cron) and [anacron(8)](https://linux.die.net/man/8/anacron),
but comes as a simple Python library with [Huey](https://github.com/coleifer/huey)-inspired API.

## Installation

Simply `uv add handcron` or `pip install handcron`.

If you'd like to use PostgreSQL as your storage backend, install the `postgres` extra:
`uv add handcron[postgres]` or `pip install handcron[postgres]`.

## Example

```python
# my_tasks.py
from handcron import SqliteHandcron

cron = SqliteHandcron("handcron.sqlite")

@cron.periodic_task("@daily")
def my_task():
    print("Hello from my task")
```

```
$ handcron tick my_tasks.cron             # drain the queue once and exit
$ handcron serve my_tasks.cron            # drain the queue periodically
$ handcron oneshot my_tasks.cron my_task  # run a task without scheduling
$ handcron describe my_tasks.cron         # print task schedule and last run status

INFO     handcron.cli: Summary of instance 'handcron':
┌──────────┬─────────┬──────────────────────────────┬──────────────┬────────────┐
│ task     │ cron    │ last run                     │ start_date   │ end_date   │
├──────────┼─────────┼──────────────────────────────┼──────────────┼────────────┤
│ my_task  │ @daily  │ SUCCESS  2026-09-25 18:55:21 │              │            │
└──────────┴─────────┴──────────────────────────────┴──────────────┴────────────┘
```

## handcron vs. alternatives

### Celery, Huey, Apache Airflow

- _handcron_ is much less resource intensive, since it works more like a serverless function
than a background service. It won't prevent your CPU from entering a low-power state;
the machine could even be turned off most of the time.
- _handcron_ has no heavy dependencies and is easily run natively on Windows or Linux.
With _uv_, your scheduled command can be as simple as: ```uv run --with handcron handcron tick my_tasks.cron```

### Plain cron(8), Systemd timer + service

- _handcron_ can catch up with missed task runs, unlike cron(8).
- _handcron_ keeps a database of past runs and their status, it has better visibility than flat logs.
- _handcron_ allows you to define tasks on different schedules in one place.

## License

MIT – see [LICENSE.txt](./LICENSE.txt).
