from __future__ import annotations

import io
import unittest
from contextlib import redirect_stderr
from pathlib import Path
from unittest.mock import patch

from video_roughcut.cli import main
from video_roughcut.tools import DependencyError


class CliTests(unittest.TestCase):
    def test_returns_clear_error_when_dependency_check_fails(self) -> None:
        stderr = io.StringIO()
        with patch("video_roughcut.cli.require_dependencies", side_effect=DependencyError("missing auto-editor")):
            with redirect_stderr(stderr):
                exit_code = main(["/tmp/demo.mp4"])

        self.assertEqual(exit_code, 1)
        self.assertIn("missing auto-editor", stderr.getvalue())

    def test_merge_subcommand_routes_to_merge_module(self) -> None:
        with patch("video_roughcut.cli.merge_main", return_value=0) as merge_main:
            exit_code = main(["merge", "part1.mp4", "part2.mp4", "--output", "merged.mp4"])

        self.assertEqual(exit_code, 0)
        merge_main.assert_called_once_with(["part1.mp4", "part2.mp4", "--output", "merged.mp4"])
