from __future__ import annotations

from pathlib import Path

from .models import VIDEO_EXTENSIONS


def discover_input_files(input_path: Path) -> list[Path]:
    input_path = input_path.expanduser()
    if not input_path.exists():
        raise FileNotFoundError(f"Input path not found: {input_path}")
    if input_path.is_file():
        if input_path.suffix.lower() not in VIDEO_EXTENSIONS:
            raise ValueError(f"Unsupported file type: {input_path.suffix}")
        return [input_path]
    files = sorted(
        path for path in input_path.iterdir() if path.is_file() and path.suffix.lower() in VIDEO_EXTENSIONS
    )
    if not files:
        raise ValueError(f"No supported video files found in: {input_path}")
    return files


def build_output_path(source_path: Path, output_dir: Path, suffix: str) -> Path:
    return output_dir / f"{source_path.stem}{suffix}.mp4"
