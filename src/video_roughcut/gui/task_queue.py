from __future__ import annotations

import itertools
import os
import platform
import subprocess
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Callable

from .workers import LogQueue, WorkerController, run_in_thread


class TaskStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


TaskRunner = Callable[..., None]


@dataclass
class QueuedTask:
    id: int
    title: str
    runner: TaskRunner
    args: tuple = ()
    result_paths: list[Path] = field(default_factory=list)
    status: TaskStatus = TaskStatus.QUEUED
    log_queue: LogQueue = field(default_factory=LogQueue)
    controller: WorkerController | None = None
    error_message: str = ""


class TaskQueue:
    def __init__(self) -> None:
        self._ids = itertools.count(1)
        self.tasks: list[QueuedTask] = []
        self.current: QueuedTask | None = None

    def enqueue(
        self,
        title: str,
        runner: TaskRunner,
        args: tuple = (),
        result_paths: list[Path] | None = None,
    ) -> QueuedTask:
        task = QueuedTask(
            id=next(self._ids),
            title=title,
            runner=runner,
            args=args,
            result_paths=result_paths or [],
        )
        self.tasks.append(task)
        return task

    def tick(self) -> None:
        if self.current is not None:
            self._finish_current_if_done()
            if self.current is not None:
                return

        next_task = self._next_queued_task()
        if next_task is not None:
            self._start(next_task)

    def cancel_current(self) -> None:
        if self.current is not None and self.current.controller is not None:
            self.current.controller.cancel()

    def clear_finished(self) -> None:
        self.tasks = [task for task in self.tasks if task.status in {TaskStatus.QUEUED, TaskStatus.RUNNING}]

    def _next_queued_task(self) -> QueuedTask | None:
        for task in self.tasks:
            if task.status == TaskStatus.QUEUED:
                return task
        return None

    def _start(self, task: QueuedTask) -> None:
        task.status = TaskStatus.RUNNING
        task.controller = run_in_thread(task.runner, task.log_queue, task.args)
        self.current = task

    def _finish_current_if_done(self) -> None:
        task = self.current
        if task is None or task.controller is None or not task.controller.done_event.is_set():
            return

        if task.controller.cancel_event.is_set():
            task.status = TaskStatus.CANCELLED
        elif task.controller.error_message:
            task.status = TaskStatus.FAILED
            task.error_message = task.controller.error_message
        else:
            task.status = TaskStatus.COMPLETED
        self.current = None


def open_path(path: Path) -> None:
    path = path.expanduser().resolve()
    system = platform.system()
    if system == "Darwin":
        subprocess.Popen(["open", str(path)])
    elif system == "Windows":
        os.startfile(path)  # type: ignore[attr-defined]
    else:
        subprocess.Popen(["xdg-open", str(path)])
