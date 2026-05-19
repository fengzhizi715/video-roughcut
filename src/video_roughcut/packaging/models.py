from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass


@dataclass(slots=True)
class Chapter:
    index: int
    title: str


@dataclass(slots=True)
class VideoProfile:
    width: int
    height: int
    fps: int


@dataclass(slots=True)
class PackageMetadata:
    title: str
    chapters: list[Chapter]

    @property
    def slug(self) -> str:
        normalized = unicodedata.normalize("NFKD", self.title)
        ascii_only = normalized.encode("ascii", "ignore").decode("ascii").lower()
        tokens = re.findall(r"[a-z0-9]+", ascii_only)
        if tokens:
            return "-".join(tokens[:4])
        fallback = re.findall(r"\d+", self.title)
        if fallback:
            return "-".join(fallback)
        return "package"

    @classmethod
    def from_titles(cls, title: str, chapter_titles: list[str]) -> "PackageMetadata":
        chapters = [Chapter(index=index, title=chapter_title) for index, chapter_title in enumerate(chapter_titles, start=1)]
        return cls(title=title, chapters=chapters)
