from __future__ import annotations

import stat
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from video_roughcut.tools import find_tool


class ToolsTests(unittest.TestCase):
    def test_find_tool_falls_back_to_interpreter_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            fake_python = tmp_path / "python3"
            fake_tool = tmp_path / "auto-editor"
            fake_python.write_text("", encoding="utf-8")
            fake_tool.write_text("#!/bin/sh\n", encoding="utf-8")
            fake_tool.chmod(fake_tool.stat().st_mode | stat.S_IXUSR)

            with patch("video_roughcut.tools.shutil.which", return_value=None):
                with patch("video_roughcut.tools.sys.executable", str(fake_python)):
                    self.assertEqual(Path(find_tool("auto-editor")).resolve(), fake_tool.resolve())
