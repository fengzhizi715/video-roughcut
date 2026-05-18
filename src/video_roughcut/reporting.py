from __future__ import annotations

import json
from pathlib import Path

from .models import ProcessResult


def write_cut_log(results: list[ProcessResult], output_dir: Path) -> Path:
    path = output_dir / "cut_log.json"
    payload = {"results": [result.to_dict() for result in results]}
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def write_report(results: list[ProcessResult], output_dir: Path) -> Path:
    path = output_dir / "report.md"
    lines = [
        "# Rough Cut Report",
        "",
        f"- Processed files: {len(results)}",
        f"- Dry run: {'yes' if any(result.dry_run for result in results) else 'no'}",
        f"- Total removed duration: {sum(result.removed_duration for result in results):.3f}s",
        "",
    ]
    for result in results:
        lines.extend(
            [
                f"## {result.source_path.name}",
                "",
                f"- Input: `{result.source_path}`",
                f"- Output: `{result.output_path}`",
                f"- Removed segments: {len(result.removed_segments)}",
                f"- Removed duration: {result.removed_duration:.3f}s",
                f"- Before: {result.original_duration:.3f}s",
                f"- After: {result.output_duration:.3f}s",
                "",
            ]
        )
    path.write_text("\n".join(lines), encoding="utf-8")
    return path
