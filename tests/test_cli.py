from __future__ import annotations

import io
import unittest
from contextlib import redirect_stderr
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
