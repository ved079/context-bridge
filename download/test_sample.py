"""
task_scheduler.py
-----------------
A minimal async task scheduler with priority queue support.
Demonstrates asyncio, heapq, and concurrent task execution.
"""

import asyncio
import heapq
import time
from dataclasses import dataclass, field
from typing import Callable, Any


@dataclass(order=True)
class ScheduledTask:
    priority: int
    task_id: str = field(compare=False)
    callback: Callable = field(compare=False)
    args: tuple = field(compare=False, default_factory=tuple)


class TaskScheduler:
    def __init__(self):
        self._queue: list[ScheduledTask] = []
        self._running = False
        self._completed = 0

    def add_task(self, priority: int, task_id: str, callback: Callable, *args):
        task = ScheduledTask(priority=priority, task_id=task_id, callback=callback, args=args)
        heapq.heappush(self._queue, task)
        print(f"  [+] Queued: {task_id} (priority={priority})")

    async def _execute(self, task: ScheduledTask):
        print(f"  [→] Starting: {task.task_id}")
        await asyncio.sleep(0.5)  # simulate work
        result = task.callback(*task.args)
        print(f"  [✓] Done: {task.task_id} -> {result}")
        self._completed += 1

    async def run(self):
        self._running = True
        print(f"Scheduler started with {len(self._queue)} tasks")
        while self._queue and self._running:
            task = heapq.heappop(self._queue)
            await self._execute(task)
        print(f"Scheduler finished - {self._completed} tasks completed")

    def stop(self):
        self._running = False


# -- Example usage --
def double(n):
    return n * 2

def greet(name):
    return f"Hello, {name}!"

async def main():
    scheduler = TaskScheduler()
    scheduler.add_task(3, "low_priority", double, 5)
    scheduler.add_task(1, "high_priority", greet, "Claude")
    scheduler.add_task(2, "medium_priority", double, 99)
    await scheduler.run()

if __name__ == "__main__":
    asyncio.run(main())
