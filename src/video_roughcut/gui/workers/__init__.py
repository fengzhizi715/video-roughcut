from __future__ import annotations

import os
import queue
import signal
import subprocess
import threading
from dataclasses import dataclass, field
from typing import Callable


class LogQueue:
    def __init__(self) -> None:
        self._queue: queue.Queue[str] = queue.Queue()

    def put(self, msg: str) -> None:
        self._queue.put(msg)

    def get_nowait(self) -> str:
        return self._queue.get_nowait()


_POLL_INTERVAL = 150


class WorkerCancelled(RuntimeError):
    """Raised when a worker process is cancelled by the user."""


@dataclass
class WorkerController:
    cancel_event: threading.Event = field(default_factory=threading.Event)
    done_event: threading.Event = field(default_factory=threading.Event)
    thread: threading.Thread | None = None
    error_message: str = ""
    _process: subprocess.Popen[str] | None = None
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def attach_process(self, process: subprocess.Popen[str]) -> None:
        with self._lock:
            self._process = process

    def detach_process(self, process: subprocess.Popen[str]) -> None:
        with self._lock:
            if self._process is process:
                self._process = None

    def cancel(self) -> None:
        self.cancel_event.set()
        with self._lock:
            process = self._process
        if process is None or process.poll() is not None:
            return
        _terminate_process_tree(process, signal.SIGTERM)
        try:
            process.wait(timeout=1)
        except subprocess.TimeoutExpired:
            _terminate_process_tree(process, signal.SIGKILL)


def _terminate_process_tree(process: subprocess.Popen[str], sig: signal.Signals) -> None:
    if os.name == "nt":
        if sig == signal.SIGKILL:
            process.kill()
        else:
            process.terminate()
        return

    try:
        os.killpg(os.getpgid(process.pid), sig)
    except ProcessLookupError:
        return
    except Exception:
        if sig == signal.SIGKILL:
            process.kill()
        else:
            process.terminate()


def stream_command(
    command: list[str],
    log_queue: LogQueue,
    controller: WorkerController,
    cwd: str | None = None,
) -> None:
    log_queue.put(f"$ {' '.join(command)}")
    popen_kwargs = {}
    if os.name != "nt":
        popen_kwargs["start_new_session"] = True
    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        cwd=cwd,
        **popen_kwargs,
    )
    controller.attach_process(process)
    try:
        if process.stdout:
            for line in iter(process.stdout.readline, ""):
                log_queue.put(line.rstrip())
            process.stdout.close()
        process.wait()
    finally:
        controller.detach_process(process)

    if controller.cancel_event.is_set():
        log_queue.put("Cancelled.")
        raise WorkerCancelled("Command cancelled")
    if process.returncode != 0:
        raise RuntimeError(f"Command failed with exit code {process.returncode}")


def run_in_thread(
    target: Callable[..., None],
    log_queue: LogQueue,
    args: tuple = (),
) -> WorkerController:
    controller = WorkerController()

    def wrapper() -> None:
        try:
            target(log_queue, controller, *args)
        except WorkerCancelled:
            pass
        except Exception as exc:
            controller.error_message = str(exc)
            log_queue.put(f"Error: {exc}")
        finally:
            controller.done_event.set()

    thread = threading.Thread(target=wrapper, daemon=True)
    controller.thread = thread
    thread.start()
    return controller
