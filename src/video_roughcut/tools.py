from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path


class DependencyError(RuntimeError):
    """Raised when required tools are missing."""


def find_tool(name: str) -> str | None:
    resolved = shutil.which(name)
    if resolved:
        return resolved

    interpreter_dirs = [Path(sys.executable).parent, Path(sys.executable).resolve().parent]
    for interpreter_dir in interpreter_dirs:
        candidate = interpreter_dir / name
        if candidate.exists() and candidate.is_file():
            return str(candidate)
    return None


def require_dependencies() -> dict[str, str]:
    resolved = {}
    missing = []
    for tool_name in ("ffmpeg", "ffprobe", "auto-editor"):
        tool_path = find_tool(tool_name)
        if tool_path:
            resolved[tool_name] = tool_path
        else:
            missing.append(tool_name)
    if missing:
        joined = ", ".join(missing)
        raise DependencyError(
            "Missing required tools: "
            f"{joined}. Install FFmpeg and auto-editor in your virtual environment first."
        )
    for tool_name, tool_path in resolved.items():
        verify_tool(tool_name, tool_path)
    return resolved


def verify_tool(name: str, tool_path: str) -> None:
    command = [tool_path, "-version"] if name in {"ffmpeg", "ffprobe"} else [tool_path, "--version"]
    completed = subprocess.run(command, capture_output=True, text=True)
    if completed.returncode != 0:
        stderr = completed.stderr.strip() or completed.stdout.strip() or "unknown error"
        raise DependencyError(
            f"{name} is installed but not runnable: {stderr}. "
            "If this is auto-editor, try running it once in the virtual environment with network access."
        )
