from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from video_roughcut.split import (
    SplitError,
    build_split_command,
    format_time,
    parse_time,
    split_video,
)


class ParseTimeTests(unittest.TestCase):
    def test_parses_plain_seconds(self) -> None:
        self.assertEqual(parse_time("10.5"), 10.5)

    def test_parses_mm_ss(self) -> None:
        self.assertEqual(parse_time("01:30"), 90.0)

    def test_parses_hh_mm_ss(self) -> None:
        self.assertEqual(parse_time("01:00:00"), 3600.0)

    def test_parses_hh_mm_ss_mmm(self) -> None:
        self.assertAlmostEqual(parse_time("00:01:30.500"), 90.5, places=3)

    def test_parses_integer_string(self) -> None:
        self.assertEqual(parse_time("60"), 60.0)

    def test_handles_whitespace(self) -> None:
        self.assertEqual(parse_time("  00:00:05  "), 5.0)


class FormatTimeTests(unittest.TestCase):
    def test_seconds(self) -> None:
        self.assertEqual(format_time(0), "00:00:00.000")

    def test_minutes(self) -> None:
        self.assertEqual(format_time(90.5), "00:01:30.500")

    def test_hours(self) -> None:
        self.assertEqual(format_time(3661.0), "01:01:01.000")


class BuildSplitCommandTests(unittest.TestCase):
    def test_builds_copy_command(self) -> None:
        command = build_split_command(
            input_path=Path("/input.mp4"),
            output_path=Path("/output.mp4"),
            start_time=10.0,
            duration=30.0,
            reencode=False,
            overwrite=False,
        )
        self.assertEqual(
            command,
            [
                "ffmpeg",
                "-ss", "00:00:10.000",
                "-i", "/input.mp4",
                "-t", "00:00:30.000",
                "-c", "copy",
                "/output.mp4",
            ],
        )

    def test_builds_reencode_command(self) -> None:
        command = build_split_command(
            input_path=Path("/input.mp4"),
            output_path=Path("/output.mp4"),
            start_time=10.0,
            duration=30.0,
            reencode=True,
            overwrite=False,
        )
        self.assertIn("-c:v", command)
        self.assertIn("libx264", command)
        self.assertIn("-c:a", command)
        self.assertIn("aac", command)

    def test_includes_overwrite_flag(self) -> None:
        command = build_split_command(
            input_path=Path("/input.mp4"),
            output_path=Path("/output.mp4"),
            start_time=0,
            duration=10,
            overwrite=True,
        )
        self.assertEqual(command[1], "-y")


class SplitVideosTests(unittest.TestCase):
    def test_rejects_missing_input(self) -> None:
        with self.assertRaises(FileNotFoundError):
            split_video(
                input_path=Path("/nonexistent.mp4"),
                output_path=Path("/out.mp4"),
                start_time=0,
                duration=10,
            )

    def test_rejects_unsupported_extension(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            source = tmpdir_path / "input.avi"
            source.write_bytes(b"video")
            with self.assertRaisesRegex(ValueError, "Unsupported input format"):
                split_video(
                    input_path=source,
                    output_path=tmpdir_path / "output.mp4",
                    start_time=0,
                    duration=10,
                )

    def test_rejects_existing_output_without_overwrite(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            source = tmpdir_path / "input.mp4"
            output = tmpdir_path / "output.mp4"
            source.write_bytes(b"video")
            output.write_bytes(b"existing")
            with self.assertRaises(FileExistsError):
                split_video(
                    input_path=source,
                    output_path=output,
                    start_time=0,
                    duration=10,
                )

    def test_rejects_unsupported_output_extension(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            source = tmpdir_path / "input.mp4"
            source.write_bytes(b"video")
            with self.assertRaisesRegex(ValueError, "Unsupported output format"):
                split_video(
                    input_path=source,
                    output_path=tmpdir_path / "output.avi",
                    start_time=0,
                    duration=10,
                )

    def test_rejects_zero_duration(self) -> None:
        with self.assertRaisesRegex(ValueError, "Duration must be positive"):
            split_video(
                input_path=Path("/input.mp4"),
                output_path=Path("/output.mp4"),
                start_time=0,
                duration=0,
            )

    def test_rejects_negative_start_time(self) -> None:
        with self.assertRaisesRegex(ValueError, "Start time must be non-negative"):
            split_video(
                input_path=Path("/input.mp4"),
                output_path=Path("/output.mp4"),
                start_time=-1,
                duration=10,
            )

    def test_wraps_ffmpeg_failures(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            source = tmpdir_path / "input.mp4"
            output = tmpdir_path / "output.mp4"
            source.write_bytes(b"video")

            with patch("video_roughcut.split._require_ffmpeg", return_value="ffmpeg"):
                with patch("video_roughcut.split.subprocess.run") as run_mock:
                    run_mock.return_value.returncode = 1
                    run_mock.return_value.stderr = "invalid data"

                    with self.assertRaisesRegex(SplitError, "invalid data"):
                        split_video(source, output, 0, 10)

    def test_calls_ffmpeg_with_correct_args(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            source = tmpdir_path / "input.mp4"
            output = tmpdir_path / "output.mp4"
            source.write_bytes(b"video")

            captured: dict = {}

            def fake_run(command: list[str], capture_output: bool, text: bool):
                captured["command"] = command

                class Result:
                    returncode = 0
                    stderr = ""

                return Result()

            with patch("video_roughcut.split._require_ffmpeg", return_value="/usr/bin/ffmpeg"):
                with patch("video_roughcut.split.subprocess.run", side_effect=fake_run) as run_mock:
                    split_video(source, output, 5, 15)

            self.assertEqual(run_mock.call_count, 1)
            self.assertEqual(captured["command"][0], "/usr/bin/ffmpeg")
            self.assertEqual(captured["command"][2], "00:00:05.000")
            self.assertEqual(captured["command"][6], "00:00:15.000")
            self.assertIn("-c", captured["command"])
            self.assertIn("copy", captured["command"])
