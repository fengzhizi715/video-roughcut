from __future__ import annotations

import json
import platform
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(frozen=True)
class RoughCutPreset:
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


DEFAULT_PRESETS: dict[str, RoughCutPreset] = {
    "high": RoughCutPreset(
        silence_threshold=-35.0,
        min_silence_duration=0.6,
        padding_before=0.25,
        padding_after=0.25,
        min_clip_duration=0.5,
        quality_profile="high",
        video_codec="libx264",
        audio_codec="aac",
        video_crf=18,
        video_preset="slow",
        audio_bitrate="192k",
        output_suffix="_rough",
    ),
    "standard": RoughCutPreset(
        silence_threshold=-35.0,
        min_silence_duration=0.6,
        padding_before=0.25,
        padding_after=0.25,
        min_clip_duration=0.5,
        quality_profile="standard",
        video_codec="libx264",
        audio_codec="aac",
        video_crf=23,
        video_preset="medium",
        audio_bitrate="128k",
        output_suffix="_rough",
    ),
}


class PresetStore:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or default_preset_path()
        self.last_error = ""
        self._presets = self._load()

    def names(self) -> list[str]:
        return sorted(self._presets)

    def get(self, name: str) -> RoughCutPreset:
        return self._presets[name]

    def save(self, name: str, preset: RoughCutPreset) -> None:
        clean_name = name.strip()
        if not clean_name:
            raise ValueError("Preset name cannot be empty.")
        previous = self._presets.get(clean_name)
        self._presets[clean_name] = preset
        try:
            self._write()
        except OSError as exc:
            if previous is None:
                self._presets.pop(clean_name, None)
            else:
                self._presets[clean_name] = previous
            raise ValueError(f"Failed to save presets: {exc}") from exc

    def _load(self) -> dict[str, RoughCutPreset]:
        presets = dict(DEFAULT_PRESETS)
        if not self.path.exists():
            return presets

        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            self.last_error = f"Failed to load presets: {exc}"
            return presets
        if not isinstance(data, dict):
            self.last_error = "Failed to load presets: top-level value must be an object."
            return presets
        for name, values in data.items():
            if not isinstance(name, str) or not isinstance(values, dict):
                continue
            try:
                presets[name] = RoughCutPreset(**values)
            except (TypeError, ValueError) as exc:
                self.last_error = f"Failed to load preset {name}: {exc}"
        return presets

    def _write(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        data = {name: asdict(preset) for name, preset in self._presets.items()}
        self.path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")


def default_preset_path(platform_name: str | None = None) -> Path:
    system = platform_name or platform.system()
    home = Path.home()
    if system == "Darwin":
        return home / "Library" / "Application Support" / "video-roughcut" / "roughcut-presets.json"
    if system == "Windows":
        return home / "AppData" / "Roaming" / "video-roughcut" / "roughcut-presets.json"
    return home / ".config" / "video-roughcut" / "roughcut-presets.json"
