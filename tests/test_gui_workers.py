from __future__ import annotations

import importlib.util
import importlib.machinery
import sys
import tempfile
import threading
import tomllib
import unittest
from pathlib import Path
from unittest.mock import patch

GUI_DIR = Path(__file__).resolve().parents[1] / "src" / "video_roughcut" / "gui"
WORKERS_DIR = GUI_DIR / "workers"


def _ensure_gui_packages() -> None:
    gui_package = sys.modules.get("video_roughcut.gui")
    if gui_package is None:
        gui_package = importlib.util.module_from_spec(
            importlib.machinery.ModuleSpec("video_roughcut.gui", loader=None)
        )
        gui_package.__path__ = [str(GUI_DIR)]
        sys.modules["video_roughcut.gui"] = gui_package

    workers_package = sys.modules.get("video_roughcut.gui.workers")
    if workers_package is None:
        workers_package = importlib.util.module_from_spec(
            importlib.machinery.ModuleSpec("video_roughcut.gui.workers", loader=None)
        )
        workers_package.__path__ = [str(WORKERS_DIR)]
        sys.modules["video_roughcut.gui.workers"] = workers_package


def _load_module(name: str, relative_path: str):
    _ensure_gui_packages()
    module_path = GUI_DIR / relative_path
    spec = importlib.util.spec_from_file_location(name, module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


workers_module = _load_module("video_roughcut.gui.workers", "workers/__init__.py")
merge_worker_module = _load_module("video_roughcut.gui.workers.merge_worker", "workers/merge_worker.py")
split_worker_module = _load_module("video_roughcut.gui.workers.split_worker", "workers/split_worker.py")

LogQueue = workers_module.LogQueue
run_in_thread = workers_module.run_in_thread
run_merge = merge_worker_module.run_merge
run_split = split_worker_module.run_split


class FakeUiDispatcher:
    def __init__(self) -> None:
        self.thread_ids: list[int] = []

    def dispatch(self, callback) -> None:
        self.thread_ids.append(threading.get_ident())
        callback()


class RunInThreadTests(unittest.TestCase):
    def test_worker_marks_done_without_invoking_ui_callback(self) -> None:
        log_queue = LogQueue()

        def target(queue: LogQueue, controller) -> None:
            queue.put("done")

        controller = run_in_thread(target, log_queue)
        controller.thread.join(timeout=2)

        self.assertFalse(controller.thread.is_alive())
        self.assertTrue(controller.done_event.is_set())

    def test_cancel_marks_controller_as_cancelled(self) -> None:
        log_queue = LogQueue()
        release = threading.Event()

        def target(queue: LogQueue, controller) -> None:
            release.wait(timeout=2)

        controller = run_in_thread(target, log_queue)

        controller.cancel()
        release.set()
        controller.thread.join(timeout=2)

        self.assertTrue(controller.cancel_event.is_set())

    def test_cancel_terminates_attached_process_group(self) -> None:
        process = FakeProcess(pid=4321)
        controller = workers_module.WorkerController()
        controller.attach_process(process)

        with patch("video_roughcut.gui.workers.os.killpg") as killpg_mock:
            with patch("video_roughcut.gui.workers.os.getpgid", return_value=9876):
                controller.cancel()

        killpg_mock.assert_called_once()
        self.assertEqual(killpg_mock.call_args.args[0], 9876)


class FakeProcess:
    def __init__(self, pid: int) -> None:
        self.pid = pid
        self.terminated = False
        self.killed = False

    def poll(self):
        return None

    def terminate(self) -> None:
        self.terminated = True

    def kill(self) -> None:
        self.killed = True

    def wait(self, timeout: float | None = None) -> int:
        return 0


class GuiWorkerIntegrationTests(unittest.TestCase):
    def test_merge_worker_reuses_core_merge_function(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            first = tmpdir_path / "part1.mp4"
            second = tmpdir_path / "part2.mp4"
            output = tmpdir_path / "merged.mp4"
            first.write_bytes(b"video")
            second.write_bytes(b"video")
            log_queue = LogQueue()

            with patch("video_roughcut.gui.workers.merge_worker.merge_videos") as merge_videos_mock:
                run_merge(log_queue, None, [first, second], output, False)

            merge_videos_mock.assert_called_once()
            args = merge_videos_mock.call_args.args
            self.assertEqual(args[:3], ([first, second], output, False))

    def test_split_worker_reuses_core_split_function(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            source = tmpdir_path / "input.mp4"
            output = tmpdir_path / "output.mp4"
            source.write_bytes(b"video")
            log_queue = LogQueue()

            with patch("video_roughcut.gui.workers.split_worker.split_video") as split_video_mock:
                run_split(log_queue, None, source, output, 5.0, 10.0, False, False)

            split_video_mock.assert_called_once()
            args = split_video_mock.call_args.args
            self.assertEqual(args[:4], (source, output, 5.0, 10.0))


class PackagingMetadataTests(unittest.TestCase):
    def test_pyproject_declares_customtkinter_dependency(self) -> None:
        pyproject_path = Path(__file__).resolve().parents[1] / "pyproject.toml"
        data = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))

        dependencies = data["project"]["dependencies"]
        self.assertTrue(any(dep.startswith("customtkinter") for dep in dependencies))

    def test_requirements_include_customtkinter(self) -> None:
        requirements_path = Path(__file__).resolve().parents[1] / "requirements.txt"
        requirements = requirements_path.read_text(encoding="utf-8").splitlines()

        self.assertTrue(any(line.startswith("customtkinter") for line in requirements))

    def test_run_sh_checks_auto_editor_before_gui_launch(self) -> None:
        run_sh_path = Path(__file__).resolve().parents[1] / "run.sh"
        run_sh = run_sh_path.read_text(encoding="utf-8")
        gui_block = run_sh.split('if [[ "${1:-}" == "--gui" ]]; then', 1)[1].split("fi", 1)[0]

        self.assertIn('require_system_tool "auto-editor"', gui_block)
