from __future__ import annotations

import argparse
import tempfile
import unittest
from pathlib import Path

from video_roughcut.config import ConfigError, build_config


class BuildConfigTests(unittest.TestCase):
    def test_cli_overrides_yaml(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            config_path = tmp_path / "config.yaml"
            input_path = tmp_path / "input.mp4"
            input_path.write_text("x", encoding="utf-8")
            config_path.write_text(
                "\n".join(
                    [
                        f"input_dir: {input_path}",
                        "output_dir: rendered",
                        "silence_threshold: -40",
                        "quality_profile: standard",
                        "video_codec: h264_videotoolbox",
                        "overwrite: false",
                    ]
                ),
                encoding="utf-8",
            )
            args = argparse.Namespace(
                input=None,
                config=str(config_path),
                output_dir="custom-output",
                silence_threshold=-32.0,
                min_silence_duration=None,
                padding_before=None,
                padding_after=None,
                min_clip_duration=None,
                quality_profile="high",
                video_codec="libx264",
                audio_codec=None,
                video_crf=16,
                video_preset="slower",
                audio_bitrate=None,
                output_suffix=None,
                overwrite=True,
                dry_run=False,
            )

            config = build_config(args)

            self.assertEqual(config.output_dir, Path("custom-output"))
            self.assertEqual(config.silence_threshold, -32.0)
            self.assertEqual(config.quality_profile, "high")
            self.assertEqual(config.video_codec, "libx264")
            self.assertEqual(config.video_crf, 16)
            self.assertEqual(config.video_preset, "slower")
            self.assertTrue(config.overwrite)

    def test_missing_input_raises(self) -> None:
        args = argparse.Namespace(
            input=None,
            config=None,
            output_dir=None,
            silence_threshold=None,
            min_silence_duration=None,
            padding_before=None,
            padding_after=None,
            min_clip_duration=None,
            quality_profile=None,
            video_codec=None,
            audio_codec=None,
            video_crf=None,
            video_preset=None,
            audio_bitrate=None,
            output_suffix=None,
            overwrite=False,
            dry_run=False,
        )
        with self.assertRaises(ConfigError):
            build_config(args)

    def test_explicit_missing_config_raises(self) -> None:
        args = argparse.Namespace(
            input="/tmp/input.mp4",
            config="/tmp/does-not-exist-video-roughcut.yaml",
            output_dir=None,
            silence_threshold=None,
            min_silence_duration=None,
            padding_before=None,
            padding_after=None,
            min_clip_duration=None,
            quality_profile=None,
            video_codec=None,
            audio_codec=None,
            video_crf=None,
            video_preset=None,
            audio_bitrate=None,
            output_suffix=None,
            overwrite=False,
            dry_run=False,
        )
        with self.assertRaisesRegex(ConfigError, "Config file not found"):
            build_config(args)

    def test_invalid_quality_profile_raises(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            input_path = tmp_path / "input.mp4"
            input_path.write_text("x", encoding="utf-8")
            args = argparse.Namespace(
                input=str(input_path),
                config=None,
                output_dir=None,
                silence_threshold=None,
                min_silence_duration=None,
                padding_before=None,
                padding_after=None,
                min_clip_duration=None,
                quality_profile="cinema",
                video_codec=None,
                audio_codec=None,
                video_crf=None,
                video_preset=None,
                audio_bitrate=None,
                output_suffix=None,
                overwrite=False,
                dry_run=False,
            )
            with self.assertRaises(ConfigError):
                build_config(args)
