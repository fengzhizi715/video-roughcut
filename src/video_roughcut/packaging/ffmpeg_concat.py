from __future__ import annotations

import subprocess
from pathlib import Path

from .models import VideoProfile


class ConcatError(RuntimeError):
    """Raised when ffmpeg concat fails."""


def build_concat_command(
    intro_path: Path,
    main_path: Path,
    outro_path: Path,
    output_path: Path,
    profile: VideoProfile,
) -> list[str]:
    return [
        "ffmpeg",
        "-y",
        "-i",
        str(intro_path),
        "-i",
        str(main_path),
        "-i",
        str(outro_path),
        "-filter_complex",
        (
            f"[0:v]scale={profile.width}:{profile.height},fps={profile.fps},setsar=1[v0];"
            f"[1:v]scale={profile.width}:{profile.height},fps={profile.fps},setsar=1[v1];"
            f"[2:v]scale={profile.width}:{profile.height},fps={profile.fps},setsar=1[v2];"
            "[v0][0:a][v1][1:a][v2][2:a]"
            "concat=n=3:v=1:a=1[v][a]"
        ),
        "-map",
        "[v]",
        "-map",
        "[a]",
        "-c:v",
        "libx264",
        "-crf",
        "16",
        "-preset",
        "slower",
        "-c:a",
        "aac",
        "-b:a",
        "256k",
        str(output_path),
    ]


def concat_videos(
    intro_path: Path,
    main_path: Path,
    outro_path: Path,
    output_path: Path,
    profile: VideoProfile,
) -> None:
    command = build_concat_command(intro_path, main_path, outro_path, output_path, profile)
    completed = subprocess.run(command, capture_output=True, text=True)
    if completed.returncode != 0:
        raise ConcatError(
            "ffmpeg concat failed.\n"
            f"Command: {' '.join(command)}\n"
            f"stderr: {completed.stderr.strip() or '(empty)'}"
        )
