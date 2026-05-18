from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from video_roughcut.models import ProcessResult, RemovedSegment
from video_roughcut.reporting import write_cut_log, write_report


class ReportingTests(unittest.TestCase):
    def test_writes_json_and_markdown(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            result = ProcessResult(
                source_path=Path("/tmp/input.mp4"),
                output_path=Path("/tmp/output.mp4"),
                parameters={"silence_threshold": -35},
                removed_segments=[RemovedSegment(start=1.0, end=2.0, duration=1.0)],
                removed_duration=1.0,
                original_duration=10.0,
                output_duration=9.0,
                dry_run=True,
                backend="auto-editor",
            )

            json_path = write_cut_log([result], tmp_path)
            report_path = write_report([result], tmp_path)

            self.assertTrue(json_path.exists())
            self.assertTrue(report_path.exists())
            self.assertIn("Rough Cut Report", report_path.read_text(encoding="utf-8"))
