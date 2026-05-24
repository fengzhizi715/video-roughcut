from __future__ import annotations

from pathlib import Path

from .backends.base import EditorBackend
from .discovery import build_output_path, discover_input_files
from .models import AppConfig, ProcessResult


def run_batch(config: AppConfig, backend: EditorBackend) -> list[ProcessResult]:
    config.output_dir.mkdir(parents=True, exist_ok=True)
    results: list[ProcessResult] = []
    for source_path in discover_input_files(config.input_path):
        output_path = build_output_path(source_path, config.output_dir, config.output_suffix)
        if not config.dry_run and output_path.exists() and not config.overwrite:
            raise FileExistsError(f"Output exists, use --overwrite to replace it: {output_path}")
        analysis = backend.analyze(source_path, config)
        if not config.dry_run:
            backend.render(source_path, output_path, config)
        results.append(
            ProcessResult(
                source_path=source_path,
                output_path=output_path,
                parameters=config.to_dict(),
                removed_segments=analysis.removed_segments,
                removed_duration=analysis.removed_duration,
                original_duration=analysis.original_duration,
                output_duration=analysis.output_duration,
                dry_run=config.dry_run,
                backend=backend.name,
            )
        )
    return results
