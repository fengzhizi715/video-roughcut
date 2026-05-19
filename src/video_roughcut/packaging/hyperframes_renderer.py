from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from .models import VideoProfile


class HyperFramesError(RuntimeError):
    """Raised when HyperFrames render fails."""


def build_render_command(project_dir: Path, output_path: Path, profile: VideoProfile) -> list[str]:
    return [
        "npx",
        "hyperframes",
        "render",
        "--quality",
        "high",
        "--fps",
        str(profile.fps),
        "--output",
        str(output_path),
    ]


def render_project(project_dir: Path, output_path: Path, profile: VideoProfile) -> None:
    command = build_render_command(project_dir, output_path, profile)
    completed = subprocess.run(command, cwd=project_dir, capture_output=True, text=True)
    if completed.returncode != 0:
        raise HyperFramesError(
            "HyperFrames render failed.\n"
            f"Command: {' '.join(command)}\n"
            f"stderr: {completed.stderr.strip() or '(empty)'}"
        )


def ensure_hyperframes_available() -> None:
    if shutil.which("npx") is None:
        raise HyperFramesError("npx not found. Install Node.js 22+ first.")
