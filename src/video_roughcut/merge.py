from __future__ import annotations

import argparse
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Callable

from .tools import DependencyError, find_tool, verify_tool

SUPPORTED_EXTENSIONS = {".mp4", ".mov", ".mkv"}


class MergeError(RuntimeError):
    """Raised when ffmpeg merge fails."""


def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Merge split recording files into one source video.")
    parser.add_argument("inputs", nargs="+", help="Input video files in merge order.")
    parser.add_argument("--output", required=True, help="Path to the merged output video.")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing output")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = create_parser().parse_args(argv)
    try:
        input_paths = [Path(value).expanduser().resolve() for value in args.inputs]
        output_path = Path(args.output).expanduser().resolve()
        merge_videos(input_paths, output_path, overwrite=args.overwrite)
    except (DependencyError, FileNotFoundError, FileExistsError, ValueError, MergeError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    print(f"Merged video: {output_path}")
    return 0


def build_merge_command(list_path: Path, output_path: Path, overwrite: bool) -> list[str]:
    command = ["ffmpeg"]
    if overwrite:
        command.append("-y")
    command.extend(
        [
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(list_path),
            "-c",
            "copy",
            str(output_path),
        ]
    )
    return command


def merge_videos(
    input_paths: list[Path],
    output_path: Path,
    overwrite: bool,
    command_runner: Callable[[list[str]], None] | None = None,
) -> None:
    if len(input_paths) < 2:
        raise ValueError("merge requires at least two input files.")
    for input_path in input_paths:
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

    with tempfile.TemporaryDirectory(prefix="video-roughcut-merge-") as tmpdir:
        list_path = Path(tmpdir) / "merge_list.txt"
        list_path.write_text(_build_concat_list(input_paths), encoding="utf-8")
        command = build_merge_command(list_path, output_path, overwrite=overwrite)
        command[0] = ffmpeg_path
        if command_runner is not None:
            command_runner(command)
            return
        completed = subprocess.run(command, capture_output=True, text=True)
        if completed.returncode != 0:
            raise MergeError(
                "ffmpeg merge failed. Input files may not share the same codecs, resolution, or stream layout.\n"
                f"Command: {' '.join(command)}\n"
                f"stderr: {completed.stderr.strip() or '(empty)'}"
            )


def _build_concat_list(input_paths: list[Path]) -> str:
    return "".join(f"file '{_escape_concat_path(path)}'\n" for path in input_paths)


def _escape_concat_path(path: Path) -> str:
    return str(path).replace("'", r"'\''")


def _require_ffmpeg() -> str:
    ffmpeg_path = find_tool("ffmpeg")
    if ffmpeg_path is None:
        raise DependencyError("Missing required tool: ffmpeg. Install FFmpeg first.")
    verify_tool("ffmpeg", ffmpeg_path)
    return ffmpeg_path
