from __future__ import annotations

import argparse
import sys

from .backends.auto_editor import AutoEditorBackend, BackendError
from .config import ConfigError, build_config
from .reporting import write_cut_log, write_report
from .runner import run_batch
from .tools import DependencyError, require_dependencies


def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Auto rough-cut videos by removing silence and long pauses.")
    parser.add_argument("input", nargs="?", help="Input video file or directory.")
    parser.add_argument("--config", default="config.yaml", help="Path to config.yaml")
    parser.add_argument("--output-dir", help="Override output directory")
    parser.add_argument("--silence-threshold", type=float, help="Silence threshold in dB, e.g. -35")
    parser.add_argument("--min-silence-duration", type=float, help="Minimum silence duration in seconds")
    parser.add_argument("--padding-before", type=float, help="Keep this many seconds before a silence cut")
    parser.add_argument("--padding-after", type=float, help="Keep this many seconds after a silence cut")
    parser.add_argument("--min-clip-duration", type=float, help="Minimum kept clip duration in seconds")
    parser.add_argument("--quality-profile", choices=("standard", "high"), help="Quality preset for export")
    parser.add_argument("--video-codec", help="Video codec for output, e.g. libx264")
    parser.add_argument("--audio-codec", help="Audio codec for output, e.g. aac")
    parser.add_argument("--video-crf", type=int, help="Video CRF quality value, lower is higher quality")
    parser.add_argument("--video-preset", help="Video encoder preset, e.g. medium or slow")
    parser.add_argument("--audio-bitrate", help="Audio bitrate, e.g. 192k")
    parser.add_argument("--output-suffix", help="Output suffix, default: _rough")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing outputs")
    parser.add_argument("--dry-run", action="store_true", help="Analyze only, do not render videos")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = create_parser()
    args = parser.parse_args(argv)
    try:
        require_dependencies()
        config = build_config(args)
        results = run_batch(config, AutoEditorBackend())
        cut_log = write_cut_log(results, config.output_dir)
        report = write_report(results, config.output_dir)
    except (DependencyError, ConfigError, FileNotFoundError, FileExistsError, ValueError, BackendError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    print(f"Processed {len(results)} file(s).")
    print(f"cut_log.json: {cut_log}")
    print(f"report.md: {report}")
    if config.dry_run:
        print("Dry-run mode: no output videos were generated.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
