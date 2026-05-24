from __future__ import annotations

import unittest
from pathlib import Path

from video_roughcut.backends.auto_editor import build_render_command, compress_silences, parse_silencedetect_output
from video_roughcut.models import AppConfig


class BackendTests(unittest.TestCase):
    def test_build_render_command_avoids_legacy_export_flag(self) -> None:
        config = AppConfig(
            input_path=Path("/tmp/input.mp4"),
            output_dir=Path("/tmp/out"),
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
            overwrite=False,
            dry_run=False,
            config_path=None,
        )

        command = build_render_command(Path("/tmp/input.mp4"), Path("/tmp/out/input_rough.mp4"), config)

        self.assertNotIn("--export", command)
        self.assertIn("--no-open", command)
        self.assertIn("-o", command)
        self.assertIn("--video-codec", command)
        self.assertIn("libx264", command)
        self.assertIn("--audio-codec", command)
        self.assertIn("aac", command)
        self.assertIn("-crf", command)
        self.assertIn("18", command)
        self.assertIn("--preset", command)
        self.assertIn("slow", command)
        self.assertIn("--audio-bitrate", command)
        self.assertIn("192k", command)

    def test_build_render_command_applies_smoothing_rules_without_deprecated_speed_flags(self) -> None:
        config = AppConfig(
            input_path=Path("/tmp/input.mp4"),
            output_dir=Path("/tmp/out"),
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
            overwrite=False,
            dry_run=False,
            config_path=None,
        )

        command = build_render_command(Path("/tmp/input.mp4"), Path("/tmp/out/input_rough.mp4"), config)

        self.assertNotIn("--silent-speed", command)
        self.assertNotIn("--video-speed", command)
        self.assertIn("--when-inactive", command)
        self.assertIn("cut", command)
        self.assertIn("--when-active", command)
        self.assertIn("nil", command)
        self.assertIn("--smooth", command)
        self.assertIn("0.6s,0.5s", command)

    def test_parse_silencedetect_output(self) -> None:
        output = """
        [silencedetect @ 0x0] silence_start: 1.2
        [silencedetect @ 0x0] silence_end: 2.4 | silence_duration: 1.2
        """

        segments = parse_silencedetect_output(output)

        self.assertEqual(len(segments), 1)
        self.assertAlmostEqual(segments[0].start, 1.2)
        self.assertAlmostEqual(segments[0].end, 2.4)

    def test_compress_silences_applies_padding(self) -> None:
        silences = parse_silencedetect_output(
            """
            silence_start: 1.0
            silence_end: 2.0 | silence_duration: 1.0
            """
        )

        segments = compress_silences(
            silences=silences,
            total_duration=10.0,
            padding_before=0.25,
            padding_after=0.25,
            min_silence_duration=0.6,
            min_clip_duration=0.5,
        )

        self.assertEqual(len(segments), 1)
        self.assertAlmostEqual(segments[0].start, 1.25)
        self.assertAlmostEqual(segments[0].end, 1.75)
