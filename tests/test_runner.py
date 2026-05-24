from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from video_roughcut.models import AnalysisResult, AppConfig
from video_roughcut.runner import run_batch


class FakeBackend:
    name = "fake"

    def __init__(self) -> None:
        self.render_calls = 0

    def analyze(self, source_path: Path, config: AppConfig) -> AnalysisResult:
        return AnalysisResult(
            source_path=source_path,
            detected_silences=[],
            removed_segments=[],
            original_duration=10.0,
            output_duration=10.0,
        )

    def render(self, source_path: Path, output_path: Path, config: AppConfig) -> None:
        self.render_calls += 1


class RunnerTests(unittest.TestCase):
    def test_dry_run_ignores_existing_output_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            source_path = tmp_path / "input.mp4"
            output_dir = tmp_path / "outputs"
            source_path.write_bytes(b"video")
            output_dir.mkdir()
            (output_dir / "input_rough.mp4").write_bytes(b"existing")
            backend = FakeBackend()
            config = AppConfig(
                input_path=source_path,
                output_dir=output_dir,
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
                dry_run=True,
                config_path=None,
            )

            results = run_batch(config, backend)

            self.assertEqual(len(results), 1)
            self.assertEqual(backend.render_calls, 0)
