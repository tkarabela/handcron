from handcron import SqliteHandcron

cron = SqliteHandcron(":memory:")

@cron.periodic_task("@daily")
def my_task():
    print("Hello from my task")

@cron.periodic_task("@weekly")
def my_task2():
    print("Hello from my task")
    raise RuntimeError
