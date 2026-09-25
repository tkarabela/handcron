# 🕐 handcron 💁

_Lightweight Python library for periodic tasks_

Unlike a traditional task queue, _handcron_ is designed to process
due tasks and then stop - by default, there is no long-running process in the background. 
Instead, you periodically run `handcron tick` yourself (from a cron, etc.).

It is similar to [django-cron](https://github.com/Tivix/django-cron) and [anacron(8)](https://linux.die.net/man/8/anacron),
but comes as a simple Python library with [Huey](https://github.com/coleifer/huey)-inspired API.

## Example

```python
# my_tasks.py
from handcron import SqliteHandcron

cron = SqliteHandcron("handcron.sqlite")

@cron.periodic_task("@daily")
def my_task():
    print("Hello from my task")
```

```shell
handcron tick my_tasks.cron             # drain the queue once and exit
handcron serve my_tasks.cron            # drain the queue periodically
handcron oneshot my_tasks.cron my_task  # run a task without scheduling
handcron describe my_tasks.cron         # print task schedule and last run status
```

## handcron vs. alternatives

### Celery, Huey, Apache Airflow

- _handcron_ is much less resource intensive, since it works more like a serverless function
than a background service. It won't prevent your CPU from entering a low-power state;
the machine could even be turned off most of the time.
- _handcron_ has no heavy dependencies and is easily run natively on Windows or Linux.
With _uv_, your scheduled command can be as simple as: ```uv run --with handcron handcron my_tasks.cron```

### Plain cron(8), Systemd timer + service

- _handcron_ can catch up with missed task runs, unlike cron(8).
- _handcron_ keeps a database of past runs and their status, it has better visibility than flat logs.
- _handcron_ allows you to define tasks on different schedules in one place.

## License

MIT – see [LICENSE.txt](./LICENSE.txt).
