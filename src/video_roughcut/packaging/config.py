from __future__ import annotations

from pathlib import Path

import yaml

from .models import PackageMetadata


class MetadataError(ValueError):
    """Raised when metadata.yaml is invalid."""


def load_metadata(path: Path) -> PackageMetadata:
    if not path.exists():
        raise MetadataError(f"Metadata file not found: {path}")
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    if not isinstance(data, dict):
        raise MetadataError("metadata yaml must contain a top-level mapping.")

    title = str(data.get("title", "")).strip()
    if not title:
        raise MetadataError("metadata title is required.")

    raw_chapters = data.get("chapters", [])
    if not isinstance(raw_chapters, list):
        raise MetadataError("metadata chapters must be a list.")

    chapter_titles: list[str] = []
    for item in raw_chapters:
        if not isinstance(item, dict):
            raise MetadataError("each chapter entry must be an object with a title field.")
        chapter_title = str(item.get("title", "")).strip()
        if not chapter_title:
            raise MetadataError("each chapter title is required.")
        chapter_titles.append(chapter_title)

    return PackageMetadata.from_titles(title, chapter_titles)
