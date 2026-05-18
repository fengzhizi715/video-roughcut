from __future__ import annotations

from pathlib import Path

import yaml

from .models import AppConfig


DEFAULT_CONFIG_PATH = Path("config.yaml")
QUALITY_PROFILES = {
    "standard": {
        "video_codec": "libx264",
        "audio_codec": "aac",
        "video_crf": 23,
        "video_preset": "medium",
        "audio_bitrate": "128k",
    },
    "high": {
        "video_codec": "libx264",
        "audio_codec": "aac",
        "video_crf": 18,
        "video_preset": "slow",
        "audio_bitrate": "192k",
    },
}


class ConfigError(ValueError):
    """Raised when config values are invalid."""


def load_yaml_config(path: Path | None) -> dict:
    if path is None:
        return {}
    if not path.exists():
        raise ConfigError(f"Config file not found: {path}")
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    if not isinstance(data, dict):
        raise ConfigError("Config file must contain a top-level mapping.")
    return data


def build_config(args) -> AppConfig:
    config_path = Path(args.config).expanduser() if args.config else DEFAULT_CONFIG_PATH
    yaml_data = load_yaml_config(config_path if config_path.exists() else None)

    input_value = args.input or yaml_data.get("input_dir")
    if not input_value:
        raise ConfigError("Provide an input file/directory via --input or config.yaml input_dir.")

    output_dir = Path(args.output_dir or yaml_data.get("output_dir", "outputs")).expanduser()
    output_suffix = args.output_suffix or yaml_data.get("output_suffix", "_rough")
    quality_profile = (args.quality_profile or yaml_data.get("quality_profile", "high")).lower()
    if quality_profile not in QUALITY_PROFILES:
        raise ConfigError(
            f"quality_profile must be one of: {', '.join(sorted(QUALITY_PROFILES))}."
        )
    profile_defaults = QUALITY_PROFILES[quality_profile]

    config = AppConfig(
        input_path=Path(input_value).expanduser(),
        output_dir=output_dir,
        silence_threshold=float(
            args.silence_threshold
            if args.silence_threshold is not None
            else yaml_data.get("silence_threshold", -35)
        ),
        min_silence_duration=float(
            args.min_silence_duration
            if args.min_silence_duration is not None
            else yaml_data.get("min_silence_duration", 0.6)
        ),
        padding_before=float(
            args.padding_before
            if args.padding_before is not None
            else yaml_data.get("padding_before", 0.25)
        ),
        padding_after=float(
            args.padding_after
            if args.padding_after is not None
            else yaml_data.get("padding_after", 0.25)
        ),
        min_clip_duration=float(
            args.min_clip_duration
            if args.min_clip_duration is not None
            else yaml_data.get("min_clip_duration", 0.5)
        ),
        quality_profile=quality_profile,
        video_codec=args.video_codec or yaml_data.get("video_codec", profile_defaults["video_codec"]),
        audio_codec=args.audio_codec or yaml_data.get("audio_codec", profile_defaults["audio_codec"]),
        video_crf=int(
            args.video_crf if args.video_crf is not None else yaml_data.get("video_crf", profile_defaults["video_crf"])
        ),
        video_preset=args.video_preset or yaml_data.get("video_preset", profile_defaults["video_preset"]),
        audio_bitrate=args.audio_bitrate or yaml_data.get("audio_bitrate", profile_defaults["audio_bitrate"]),
        output_suffix=output_suffix,
        overwrite=bool(args.overwrite if args.overwrite else yaml_data.get("overwrite", False)),
        dry_run=bool(args.dry_run),
        config_path=config_path if config_path.exists() else None,
    )
    validate_config(config)
    return config


def validate_config(config: AppConfig) -> None:
    if config.input_path is None:
        raise ConfigError("Input path is required.")
    if config.silence_threshold >= 0:
        raise ConfigError("silence_threshold must be a negative dB value, e.g. -35.")
    for field_name in (
        "min_silence_duration",
        "padding_before",
        "padding_after",
        "min_clip_duration",
    ):
        if getattr(config, field_name) < 0:
            raise ConfigError(f"{field_name} must be >= 0.")
    if not config.output_suffix:
        raise ConfigError("output_suffix cannot be empty.")
    if config.quality_profile not in QUALITY_PROFILES:
        raise ConfigError(
            f"quality_profile must be one of: {', '.join(sorted(QUALITY_PROFILES))}."
        )
    if not 0 <= config.video_crf <= 63:
        raise ConfigError("video_crf must be between 0 and 63.")
    for field_name in ("video_codec", "audio_codec", "video_preset", "audio_bitrate"):
        if not getattr(config, field_name):
            raise ConfigError(f"{field_name} cannot be empty.")
