from __future__ import annotations

import json
import argparse
import subprocess
import sys
from pathlib import Path

from .config import MetadataError, load_metadata
from .ffmpeg_concat import ConcatError, concat_videos
from .hyperframes_renderer import HyperFramesError, ensure_hyperframes_available, render_project
from .models import VideoProfile
from .project_builder import chapter_output_name, prepare_package_workspace, write_project


TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"


def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate HyperFrames wrappers for a rough-cut video.")
    parser.add_argument("--input", required=True, help="Path to rough_cut.mp4")
    parser.add_argument("--metadata", required=True, help="Path to metadata.yaml")
    parser.add_argument("--output-dir", default="outputs/package", help="Base output directory")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = create_parser().parse_args(argv)
    try:
        ensure_hyperframes_available()
        input_path = Path(args.input).expanduser().resolve()
        metadata_path = Path(args.metadata).expanduser().resolve()
        if not input_path.exists():
            raise FileNotFoundError(f"Input rough cut not found: {input_path}")

        metadata = load_metadata(metadata_path)
        profile = _probe_video_profile(input_path)
        package_root = Path(args.output_dir).expanduser().resolve() / metadata.slug
        paths = prepare_package_workspace(package_root, metadata_path, metadata)
        intro_project = paths["projects"] / "intro"
        outro_project = paths["projects"] / "outro"
        write_project(
            intro_project,
            TEMPLATES_DIR / "intro.html",
            {"__TITLE__": metadata.title},
            profile,
        )
        write_project(
            outro_project,
            TEMPLATES_DIR / "outro.html",
            {"__TITLE__": metadata.title},
            profile,
        )

        render_project(intro_project, paths["intro"], profile)
        _ensure_audio_track(paths["intro"])

        for chapter in metadata.chapters:
            chapter_project = paths["projects"] / f"chapter_{chapter.index:02d}"
            chapter_output = paths["chapters"] / chapter_output_name(chapter)
            write_project(
                chapter_project,
                TEMPLATES_DIR / "chapter.html",
                {
                    "__CHAPTER_NUMBER__": f"{chapter.index:02d}",
                    "__CHAPTER_TITLE__": chapter.title,
                },
                profile,
            )
            render_project(chapter_project, chapter_output, profile)

        render_project(outro_project, paths["outro"], profile)
        _ensure_audio_track(paths["outro"])
        concat_videos(paths["intro"], input_path, paths["outro"], paths["final"], profile)
    except (MetadataError, FileNotFoundError, HyperFramesError, ConcatError, RuntimeError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    print(f"Package output: {paths['root']}")
    print(f"intro.mp4: {paths['intro']}")
    print(f"outro.mp4: {paths['outro']}")
    print(f"final.mp4: {paths['final']}")
    print(f"chapter cards: {paths['chapters']}")
    return 0


def _ensure_audio_track(video_path: Path) -> None:
    muxed_path = video_path.with_name(f"{video_path.stem}_muxed.mp4")
    command = [
        "ffmpeg",
        "-y",
        "-f",
        "lavfi",
        "-i",
        "anullsrc=channel_layout=stereo:sample_rate=48000",
        "-i",
        str(video_path),
        "-shortest",
        "-c:v",
        "copy",
        "-c:a",
        "aac",
        "-b:a",
        "128k",
        str(muxed_path),
    ]
    completed = subprocess.run(command, capture_output=True, text=True)
    if completed.returncode != 0:
        raise RuntimeError(
            "Failed to add silent audio track.\n"
            f"Command: {' '.join(command)}\n"
            f"stderr: {completed.stderr.strip() or '(empty)'}"
        )
    muxed_path.replace(video_path)


def _probe_video_profile(video_path: Path) -> VideoProfile:
    command = [
        "ffprobe",
        "-v",
        "error",
        "-select_streams",
        "v:0",
        "-show_entries",
        "stream=width,height,r_frame_rate",
        "-of",
        "json",
        str(video_path),
    ]
    completed = subprocess.run(command, capture_output=True, text=True)
    if completed.returncode != 0:
        raise RuntimeError(f"ffprobe failed for {video_path}: {completed.stderr.strip()}")
    payload = json.loads(completed.stdout)
    stream = payload["streams"][0]
    return VideoProfile(
        width=int(stream["width"]),
        height=int(stream["height"]),
        fps=_parse_fps(stream["r_frame_rate"]),
    )


def _parse_fps(value: str) -> int:
    numerator, denominator = value.split("/", maxsplit=1)
    if denominator == "0":
        return 30
    return max(1, round(float(numerator) / float(denominator)))


if __name__ == "__main__":
    raise SystemExit(main())
