from __future__ import annotations

import tempfile
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch


class _FakeCTkFrame:
    pass


sys.modules.setdefault("customtkinter", types.SimpleNamespace(CTkFrame=_FakeCTkFrame))

from video_roughcut.gui.presets import PresetStore, RoughCutPreset, default_preset_path
from video_roughcut.gui.tabs.queue_tab import QueueTab
from video_roughcut.gui.task_queue import QueuedTask, TaskQueue, TaskStatus


class TaskQueueTests(unittest.TestCase):
    def test_runs_enqueued_tasks_one_at_a_time(self) -> None:
        queue = TaskQueue()
        events: list[str] = []

        def task(log_queue, controller, name: str) -> None:
            events.append(name)
            log_queue.put(f"ran {name}")

        first = queue.enqueue("first", task, args=("first",))
        second = queue.enqueue("second", task, args=("second",))

        queue.tick()
        self.assertEqual(first.status, TaskStatus.RUNNING)
        self.assertEqual(second.status, TaskStatus.QUEUED)

        first.controller.thread.join(timeout=2)
        queue.tick()
        queue.tick()

        second.controller.thread.join(timeout=2)
        queue.tick()

        self.assertEqual(events, ["first", "second"])
        self.assertEqual(first.status, TaskStatus.COMPLETED)
        self.assertEqual(second.status, TaskStatus.COMPLETED)

    def test_marks_failed_task_and_continues_with_next(self) -> None:
        queue = TaskQueue()

        def fail(log_queue, controller) -> None:
            raise RuntimeError("boom")

        def succeed(log_queue, controller) -> None:
            log_queue.put("ok")

        failed = queue.enqueue("fail", fail)
        completed = queue.enqueue("succeed", succeed)

        queue.tick()
        failed.controller.thread.join(timeout=2)
        queue.tick()
        queue.tick()
        completed.controller.thread.join(timeout=2)
        queue.tick()

        self.assertEqual(failed.status, TaskStatus.FAILED)
        self.assertIn("boom", failed.error_message)
        self.assertEqual(completed.status, TaskStatus.COMPLETED)

    def test_cancel_current_marks_task_cancelled(self) -> None:
        queue = TaskQueue()

        def long_task(log_queue, controller) -> None:
            controller.cancel_event.wait(timeout=2)

        task = queue.enqueue("long", long_task)

        queue.tick()
        queue.cancel_current()
        task.controller.thread.join(timeout=2)
        queue.tick()

        self.assertEqual(task.status, TaskStatus.CANCELLED)


class QueueTabTests(unittest.TestCase):
    def test_log_viewer_clears_when_current_task_changes(self) -> None:
        first = QueuedTask(id=1, title="first", runner=lambda: None)
        second = QueuedTask(id=2, title="second", runner=lambda: None)
        first.log_queue.put("first log")
        second.log_queue.put("second log")
        task_queue = type("FakeTaskQueue", (), {"current": first})()
        log_viewer = _FakeLogViewer()
        tab = QueueTab.__new__(QueueTab)
        tab.task_queue = task_queue
        tab.log_viewer = log_viewer
        tab._log_task_id = None

        tab._drain_current_log()
        task_queue.current = second
        tab._drain_current_log()

        self.assertEqual(log_viewer.events, [("clear", ""), ("append", "first log"), ("clear", ""), ("append", "second log")])


class _FakeLogViewer:
    def __init__(self) -> None:
        self.events: list[tuple[str, str]] = []

    def clear(self) -> None:
        self.events.append(("clear", ""))

    def append(self, line: str) -> None:
        self.events.append(("append", line))


class PresetStoreTests(unittest.TestCase):
    def test_loads_default_presets_when_file_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            store = PresetStore(Path(tmpdir) / "presets.json")

            self.assertIn("high", store.names())
            self.assertIn("standard", store.names())
            self.assertEqual(store.get("high").video_crf, 18)

    def test_saves_and_reloads_custom_preset(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "presets.json"
            store = PresetStore(path)
            preset = RoughCutPreset(
                silence_threshold=-32.0,
                min_silence_duration=0.8,
                padding_before=0.2,
                padding_after=0.35,
                min_clip_duration=0.7,
                quality_profile="standard",
                video_codec="libx264",
                audio_codec="aac",
                video_crf=22,
                video_preset="medium",
                audio_bitrate="160k",
                output_suffix="_course",
            )

            store.save("course", preset)

            reloaded = PresetStore(path)
            self.assertIn("course", reloaded.names())
            self.assertEqual(reloaded.get("course").output_suffix, "_course")
            self.assertEqual(reloaded.get("course").audio_bitrate, "160k")

    def test_corrupt_preset_file_falls_back_to_defaults(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "presets.json"
            path.write_text("{not valid json", encoding="utf-8")

            store = PresetStore(path)

            self.assertIn("high", store.names())
            self.assertIn("Failed to load presets", store.last_error)

    def test_invalid_preset_entries_are_ignored(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "presets.json"
            path.write_text('{"bad": {"video_crf": 20}}', encoding="utf-8")

            store = PresetStore(path)

            self.assertIn("high", store.names())
            self.assertNotIn("bad", store.names())

    def test_default_preset_path_uses_user_config_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("video_roughcut.gui.presets.Path.home", return_value=Path(tmpdir)):
                path = default_preset_path("Darwin")

        self.assertEqual(path, Path(tmpdir) / "Library" / "Application Support" / "video-roughcut" / "roughcut-presets.json")

    def test_save_failure_restores_previous_preset(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "presets.json"
            store = PresetStore(path)
            previous = store.get("standard")
            replacement = RoughCutPreset(
                silence_threshold=-30.0,
                min_silence_duration=0.4,
                padding_before=0.1,
                padding_after=0.1,
                min_clip_duration=0.3,
                quality_profile="standard",
                video_codec="libx264",
                audio_codec="aac",
                video_crf=20,
                video_preset="medium",
                audio_bitrate="128k",
                output_suffix="_new",
            )

            with patch.object(PresetStore, "_write", side_effect=OSError("disk full")):
                with self.assertRaisesRegex(ValueError, "Failed to save presets"):
                    store.save("standard", replacement)

            self.assertEqual(store.get("standard"), previous)
