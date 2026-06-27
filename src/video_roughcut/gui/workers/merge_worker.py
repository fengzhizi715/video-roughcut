from __future__ import annotations

from pathlib import Path

from ..workers import LogQueue, WorkerController, stream_command
from ...merge import merge_videos


def run_merge(
    log_queue: LogQueue,
    controller: WorkerController,
    input_paths: list[Path],
    output_path: Path,
    overwrite: bool,
) -> None:
    merge_videos(
        input_paths,
        output_path,
        overwrite,
        lambda command: stream_command(command, log_queue, controller),
    )
    log_queue.put(f"Merge complete: {output_path}")
