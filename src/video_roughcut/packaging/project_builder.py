from __future__ import annotations

import shutil
from pathlib import Path

from .models import Chapter, PackageMetadata, VideoProfile


DESIGN_MD = """# DESIGN

## Style Prompt
Dark technical motion graphics with deep navy and black foundations, blue-violet neon accents, precise HUD lines, scanning grids, and restrained cinematic motion. The feeling should be engineered, system-driven, and premium rather than playful.

## Colors
- `#050813` base canvas
- `#0b1427` structural surfaces
- `#6e75ff` violet signal glow
- `#19d4ff` cyan interface accent
- `#eef3ff` headline text

## Typography
- SF Pro Display
- Avenir Next

## What NOT to Do
- No cartoon illustration
- No robot motifs or mascots
- No glossy 3D blobs
- No flat purple-on-white startup aesthetic
- No chaotic glitch overload
"""


def prepare_package_workspace(output_root: Path, metadata_path: Path, metadata: PackageMetadata) -> dict[str, Path]:
    output_root.mkdir(parents=True, exist_ok=True)
    chapters_dir = output_root / "chapters"
    projects_dir = output_root / "projects"
    chapters_dir.mkdir(parents=True, exist_ok=True)
    projects_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(metadata_path, output_root / "metadata.yaml")
    return {
        "root": output_root,
        "chapters": chapters_dir,
        "projects": projects_dir,
        "final": output_root / "final.mp4",
        "intro": output_root / "intro.mp4",
        "outro": output_root / "outro.mp4",
    }


def write_project(
    project_dir: Path,
    template_path: Path,
    replacements: dict[str, str],
    profile: VideoProfile,
) -> Path:
    project_dir.mkdir(parents=True, exist_ok=True)
    (project_dir / "DESIGN.md").write_text(DESIGN_MD, encoding="utf-8")
    template = template_path.read_text(encoding="utf-8")
    replacements = {**replacements, "__WIDTH__": str(profile.width), "__HEIGHT__": str(profile.height)}
    for key, value in replacements.items():
        template = template.replace(key, value)
    index_path = project_dir / "index.html"
    index_path.write_text(template, encoding="utf-8")
    return index_path


def chapter_output_name(chapter: Chapter) -> str:
    return f"chapter_{chapter.index:02d}.mp4"
