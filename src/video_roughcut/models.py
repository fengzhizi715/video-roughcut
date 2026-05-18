from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path


VIDEO_EXTENSIONS = {".mp4", ".mov", ".mkv"}


@dataclass(slots=True)
class AppConfig:
    input_path: Path | None
    output_dir: Path
    silence_threshold: float
    min_silence_duration: float
    padding_before: float
    padding_after: float
    min_clip_duration: float
    quality_profile: str
    video_codec: str
    audio_codec: str
    video_crf: int
    video_preset: str
    audio_bitrate: str
    output_suffix: str
    overwrite: bool
    dry_run: bool
    config_path: Path | None = None

    def to_dict(self) -> dict:
        data = asdict(self)
        return {
            key: (str(value) if isinstance(value, Path) else value)
            for key, value in data.items()
        }


@dataclass(slots=True)
class RemovedSegment:
    start: float
    end: float
    duration: float

    def to_dict(self) -> dict:
        return {
            "start": round(self.start, 3),
            "end": round(self.end, 3),
            "duration": round(self.duration, 3),
        }


@dataclass(slots=True)
class AnalysisResult:
    source_path: Path
    detected_silences: list[RemovedSegment]
    removed_segments: list[RemovedSegment]
    original_duration: float
    output_duration: float

    @property
    def removed_duration(self) -> float:
        return sum(segment.duration for segment in self.removed_segments)


@dataclass(slots=True)
class ProcessResult:
    source_path: Path
    output_path: Path
    parameters: dict
    removed_segments: list[RemovedSegment]
    removed_duration: float
    original_duration: float
    output_duration: float
    dry_run: bool
    backend: str

    def to_dict(self) -> dict:
        return {
            "input_file": str(self.source_path),
            "output_file": str(self.output_path),
            "parameters": self.parameters,
            "removed_segments": [segment.to_dict() for segment in self.removed_segments],
            "removed_total_duration": round(self.removed_duration, 3),
            "duration_before": round(self.original_duration, 3),
            "duration_after": round(self.output_duration, 3),
            "dry_run": self.dry_run,
            "backend": self.backend,
        }
