from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from video_roughcut.merge import MergeError, build_merge_command, merge_videos


class MergeTests(unittest.TestCase):
    def test_build_merge_command_uses_concat_demuxer_and_stream_copy(self) -> None:
        command = build_merge_command(
            list_path=Path("/tmp/merge_list.txt"),
            output_path=Path("/tmp/merged.mp4"),
            overwrite=False,
        )

        self.assertEqual(
            command,
            [
                "ffmpeg",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                "/tmp/merge_list.txt",
                "-c",
                "copy",
                "/tmp/merged.mp4",
            ],
        )

    def test_build_merge_command_includes_overwrite_flag_when_enabled(self) -> None:
        command = build_merge_command(
            list_path=Path("/tmp/merge_list.txt"),
            output_path=Path("/tmp/merged.mp4"),
            overwrite=True,
        )

        self.assertEqual(command[:2], ["ffmpeg", "-y"])

    def test_merge_videos_writes_concat_list_in_input_order(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            input_paths = [tmpdir_path / "part 1.mp4", tmpdir_path / "part2.mp4"]
            for path in input_paths:
                path.write_bytes(b"video")
            output_path = tmpdir_path / "merged.mp4"
            captured: dict[str, str] = {}

            def fake_run(command: list[str], capture_output: bool, text: bool):
                list_path = Path(command[6])
                captured["content"] = list_path.read_text(encoding="utf-8")

                class Result:
                    returncode = 0
                    stderr = ""

                return Result()

            with patch("video_roughcut.merge._require_ffmpeg", return_value="ffmpeg"):
                with patch("video_roughcut.merge.subprocess.run", side_effect=fake_run) as run_mock:
                    merge_videos(input_paths, output_path, overwrite=False)

            self.assertEqual(
                captured["content"],
                "\n".join(
                    [
                        f"file '{input_paths[0]}'",
                        f"file '{input_paths[1]}'",
                    ]
                )
                + "\n",
            )
            self.assertEqual(run_mock.call_count, 1)

    def test_merge_videos_requires_at_least_two_inputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            source = tmpdir_path / "part1.mp4"
            source.write_bytes(b"video")

            with self.assertRaisesRegex(ValueError, "at least two input files"):
                merge_videos([source], tmpdir_path / "merged.mp4", overwrite=False)

    def test_merge_videos_rejects_unsupported_extensions(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            first = tmpdir_path / "part1.mp4"
            second = tmpdir_path / "part2.avi"
            first.write_bytes(b"video")
            second.write_bytes(b"video")

            with self.assertRaisesRegex(ValueError, "Unsupported input format"):
                merge_videos([first, second], tmpdir_path / "merged.mp4", overwrite=False)

    def test_merge_videos_rejects_existing_output_without_overwrite(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            first = tmpdir_path / "part1.mp4"
            second = tmpdir_path / "part2.mp4"
            output = tmpdir_path / "merged.mp4"
            first.write_bytes(b"video")
            second.write_bytes(b"video")
            output.write_bytes(b"existing")

            with self.assertRaises(FileExistsError):
                merge_videos([first, second], output, overwrite=False)

    def test_merge_videos_wraps_ffmpeg_failures(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            first = tmpdir_path / "part1.mp4"
            second = tmpdir_path / "part2.mp4"
            first.write_bytes(b"video")
            second.write_bytes(b"video")

            with patch("video_roughcut.merge._require_ffmpeg", return_value="ffmpeg"):
                with patch("video_roughcut.merge.subprocess.run") as run_mock:
                    run_mock.return_value.returncode = 1
                    run_mock.return_value.stderr = "codec mismatch"

                    with self.assertRaisesRegex(MergeError, "codec mismatch"):
                        merge_videos([first, second], tmpdir_path / "merged.mp4", overwrite=False)
