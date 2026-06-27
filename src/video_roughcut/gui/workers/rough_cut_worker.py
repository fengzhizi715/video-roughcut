from __future__ import annotations

import sys
from pathlib import Path

from ..workers import LogQueue, WorkerController, stream_command


def run_rough_cut(log_queue: LogQueue, controller: WorkerController, input_path: Path, output_dir: Path,
                  silence_threshold: float, min_silence_duration: float,
                  padding_before: float, padding_after: float, min_clip_duration: float,
                  quality_profile: str, video_codec: str, audio_codec: str,
                  video_crf: int, video_preset: str, audio_bitrate: str,
                  output_suffix: str, overwrite: bool, dry_run: bool) -> None:

    if not input_path.exists():
        raise FileNotFoundError(f"Input not found: {input_path}")

    cmd = [
        sys.executable, "-m", "video_roughcut.cli",
        str(input_path),
        "--output-dir", str(output_dir),
        "--silence-threshold", str(silence_threshold),
        "--min-silence-duration", str(min_silence_duration),
        "--padding-before", str(padding_before),
        "--padding-after", str(padding_after),
        "--min-clip-duration", str(min_clip_duration),
        "--quality-profile", quality_profile,
        "--video-codec", video_codec,
        "--audio-codec", audio_codec,
        "--video-crf", str(video_crf),
        "--video-preset", video_preset,
        "--audio-bitrate", audio_bitrate,
        "--output-suffix", output_suffix,
    ]

    if overwrite:
        cmd.append("--overwrite")
    if dry_run:
        cmd.append("--dry-run")

    stream_command(cmd, log_queue, controller)
    log_queue.put("Rough cut complete.")
