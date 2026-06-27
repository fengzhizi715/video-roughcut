from __future__ import annotations

from pathlib import Path

from ..workers import LogQueue, WorkerController, stream_command
from ...split import split_video


def run_split(
    log_queue: LogQueue,
    controller: WorkerController,
    input_path: Path,
    output_path: Path,
    start_time: float,
    duration: float,
    reencode: bool,
    overwrite: bool,
) -> None:
    split_video(
        input_path,
        output_path,
        start_time,
        duration,
        reencode,
        overwrite,
        lambda command: stream_command(command, log_queue, controller),
    )
    log_queue.put(f"Split complete: {output_path}")
