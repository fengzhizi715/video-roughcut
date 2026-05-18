from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from video_roughcut.discovery import build_output_path, discover_input_files


class DiscoveryTests(unittest.TestCase):
    def test_discovers_supported_videos_in_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            (tmp_path / "a.mp4").write_text("x", encoding="utf-8")
            (tmp_path / "b.mov").write_text("x", encoding="utf-8")
            (tmp_path / "skip.txt").write_text("x", encoding="utf-8")

            files = discover_input_files(tmp_path)

            self.assertEqual([file.name for file in files], ["a.mp4", "b.mov"])

    def test_builds_output_path(self) -> None:
        path = build_output_path(Path("/tmp/demo.mov"), Path("/out"), "_rough")
        self.assertEqual(path, Path("/out/demo_rough.mp4"))
