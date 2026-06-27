from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path
from typing import Callable

from .tools import DependencyError, find_tool, verify_tool

SUPPORTED_EXTENSIONS = {".mp4", ".mov", ".mkv"}


class SplitError(RuntimeError):
    """Raised when ffmpeg split fails."""


def parse_time(time_str: str) -> float:
    parts = time_str.strip().split(":")
    if len(parts) == 3:
        return float(parts[0]) * 3600 + float(parts[1]) * 60 + float(parts[2])
    elif len(parts) == 2:
        return float(parts[0]) * 60 + float(parts[1])
    else:
        return float(time_str)


def format_time(seconds: float) -> str:
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = seconds % 60
    return f"{hours:02d}:{minutes:02d}:{secs:06.3f}"


def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Split a video file by extracting a segment with start and end times."
    )
    parser.add_argument("input", help="Input video file.")
    parser.add_argument("-s", "--start", default="0", help="Start time (HH:MM:SS.mmm, MM:SS.mmm, or seconds). Default: 0")
    parser.add_argument("-e", "--end", help="End time (HH:MM:SS.mmm, MM:SS.mmm, or seconds).")
    parser.add_argument("-d", "--duration", type=float, help="Duration in seconds (alternative to --end).")
    parser.add_argument("-o", "--output", help="Output video path. Auto-generated from input name and time range if omitted.")
    parser.add_argument("--reencode", action="store_true", help="Re-encode for frame-accurate cut. Slower but precise.")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing output file.")
    return parser


def build_split_command(
    input_path: Path,
    output_path: Path,
    start_time: float,
    duration: float,
    reencode: bool = False,
    overwrite: bool = False,
) -> list[str]:
    command = ["ffmpeg"]
    if overwrite:
        command.append("-y")
    command.extend(["-ss", format_time(start_time), "-i", str(input_path), "-t", format_time(duration)])
    if reencode:
        command.extend(["-c:v", "libx264", "-c:a", "aac"])
    else:
        command.extend(["-c", "copy"])
    command.append(str(output_path))
    return command


def split_video(
    input_path: Path,
    output_path: Path,
    start_time: float,
    duration: float,
    reencode: bool = False,
    overwrite: bool = False,
    command_runner: Callable[[list[str]], None] | None = None,
) -> None:
    if duration <= 0:
        raise ValueError("Duration must be positive.")
    if start_time < 0:
        raise ValueError("Start time must be non-negative.")
    if not input_path.exists():
        raise FileNotFoundError(f"Input video not found: {input_path}")
    if input_path.suffix.lower() not in SUPPORTED_EXTENSIONS:
        raise ValueError(f"Unsupported input format: {input_path.suffix}. Supported: mp4, mov, mkv.")
    if output_path.exists() and not overwrite:
        raise FileExistsError(f"Output already exists: {output_path}")
    if output_path.suffix.lower() not in SUPPORTED_EXTENSIONS:
        raise ValueError(f"Unsupported output format: {output_path.suffix}. Supported: mp4, mov, mkv.")

    ffmpeg_path = _require_ffmpeg()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    command = build_split_command(input_path, output_path, start_time, duration, reencode, overwrite)
    command[0] = ffmpeg_path

    if command_runner is not None:
        command_runner(command)
        return

    completed = subprocess.run(command, capture_output=True, text=True)
    if completed.returncode != 0:
        raise SplitError(
            "ffmpeg split failed.\n"
            f"Command: {' '.join(command)}\n"
            f"stderr: {completed.stderr.strip() or '(empty)'}"
        )


def _require_ffmpeg() -> str:
    ffmpeg_path = find_tool("ffmpeg")
    if ffmpeg_path is None:
        raise DependencyError("Missing required tool: ffmpeg. Install FFmpeg first.")
    verify_tool("ffmpeg", ffmpeg_path)
    return ffmpeg_path


def _auto_output_path(input_path: Path, start_time: float, end_time: float) -> Path:
    stem = input_path.stem
    suffix = input_path.suffix
    start_str = format_time(start_time).replace(":", ".")
    end_str = format_time(end_time).replace(":", ".")
    return input_path.parent / f"{stem}_{start_str}-{end_str}{suffix}"


def main(argv: list[str] | None = None) -> int:
    args = create_parser().parse_args(argv)
    try:
        input_path = Path(args.input).expanduser().resolve()

        start_time = parse_time(args.start)
        if args.end is not None and args.duration is not None:
            print("Error: Specify either --end or --duration, not both.", file=sys.stderr)
            return 1
        if args.end is not None:
            end_time = parse_time(args.end)
            duration = end_time - start_time
            if duration <= 0:
                print("Error: End time must be after start time.", file=sys.stderr)
                return 1
        elif args.duration is not None:
            duration = args.duration
            end_time = start_time + duration
        else:
            print("Error: Specify --end or --duration.", file=sys.stderr)
            return 1

        if args.output:
            output_path = Path(args.output).expanduser().resolve()
        else:
            output_path = _auto_output_path(input_path, start_time, end_time)

        split_video(input_path, output_path, start_time, duration, reencode=args.reencode, overwrite=args.overwrite)
    except (DependencyError, FileNotFoundError, FileExistsError, ValueError, SplitError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    print(f"Split video: {output_path}")
    return 0
