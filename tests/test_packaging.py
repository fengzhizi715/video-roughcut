from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from video_roughcut.packaging.config import load_metadata
from video_roughcut.packaging.ffmpeg_concat import build_concat_command
from video_roughcut.packaging.hyperframes_renderer import build_render_command
from video_roughcut.packaging.models import PackageMetadata, VideoProfile


class PackagingTests(unittest.TestCase):
    def test_load_metadata_reads_title_and_chapters(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            metadata_path = Path(tmpdir) / "metadata.yaml"
            metadata_path.write_text(
                "\n".join(
                    [
                        "title: Codex 工程实践 01",
                        "chapters:",
                        "  - title: 开场",
                        "  - title: 正文",
                    ]
                ),
                encoding="utf-8",
            )

            metadata = load_metadata(metadata_path)

            self.assertEqual(metadata.title, "Codex 工程实践 01")
            self.assertEqual([chapter.title for chapter in metadata.chapters], ["开场", "正文"])

    def test_build_render_command_uses_hyperframes_render(self) -> None:
        command = build_render_command(
            Path("/tmp/card-project"),
            Path("/tmp/intro.mp4"),
            VideoProfile(width=3840, height=2146, fps=60),
        )

        self.assertEqual(command[:3], ["npx", "hyperframes", "render"])
        self.assertIn("--quality", command)
        self.assertIn("high", command)
        self.assertIn("--output", command)
        self.assertIn("--fps", command)
        self.assertIn("60", command)

    def test_build_concat_command_concatenates_intro_main_outro(self) -> None:
        command = build_concat_command(
            intro_path=Path("/tmp/intro.mp4"),
            main_path=Path("/tmp/rough_cut.mp4"),
            outro_path=Path("/tmp/outro.mp4"),
            output_path=Path("/tmp/final.mp4"),
            profile=VideoProfile(width=3840, height=2146, fps=60),
        )

        self.assertEqual(command[0], "ffmpeg")
        self.assertIn("-filter_complex", command)
        self.assertIn("concat=n=3:v=1:a=1", " ".join(command))
        self.assertIn("scale=3840:2146", " ".join(command))
        self.assertIn("fps=60", " ".join(command))
        self.assertEqual(command[-1], "/tmp/final.mp4")

    def test_metadata_slug_uses_title(self) -> None:
        metadata = PackageMetadata.from_titles("Codex 工程实践 01", ["开场"])

        self.assertEqual(metadata.slug, "codex-01")
