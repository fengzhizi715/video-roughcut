from __future__ import annotations

import queue
from pathlib import Path

import customtkinter as ctk
from tkinter import filedialog

from ..task_queue import TaskQueue
from ..workers import LogQueue, WorkerController, _POLL_INTERVAL
from ..workers.merge_worker import run_merge
from ..widgets.log_viewer import LogViewer


def _section_header(parent: ctk.CTkFrame | ctk.CTkScrollableFrame, text: str) -> ctk.CTkFrame:
    h = ctk.CTkFrame(parent, fg_color="transparent")
    h.grid_columnconfigure(0, weight=1)
    ctk.CTkLabel(h, text=text, font=ctk.CTkFont(size=13, weight="bold"), anchor="w").grid(row=0, column=0, sticky="w", padx=4, pady=(6, 2))
    ctk.CTkFrame(h, height=1, fg_color=("gray70", "gray30")).grid(row=1, column=0, sticky="ew", padx=4)
    return h


def _browse_button(parent, text, command) -> ctk.CTkButton:
    return ctk.CTkButton(parent, text=text, width=60, height=28, command=command)


class MergeTab:
    def __init__(self, tabview: ctk.CTkTabview, name: str, task_queue: TaskQueue) -> None:
        self.tab = tabview.add(name)
        self.task_queue = task_queue
        self.log_queue = LogQueue()
        self.worker: WorkerController | None = None
        self._running = False
        self._poll_job: str | None = None
        self._file_paths: list[Path] = []

        self.tab.grid_columnconfigure(0, weight=1)
        self.tab.grid_rowconfigure(0, weight=1)

        self.scroll = ctk.CTkScrollableFrame(self.tab)
        self.scroll.grid(row=0, column=0, sticky="nsew")
        self.scroll.grid_columnconfigure(0, weight=1)

        self._build_input_section()
        self._build_output_section()
        self._build_action_section()
        self._build_log_section()

    def _build_input_section(self) -> None:
        start = self.scroll.grid_size()[1]
        _section_header(self.scroll, "输入文件（按录制顺序）").grid(row=start, column=0, sticky="ew")

        f = ctk.CTkFrame(self.scroll)
        f.grid(row=start + 1, column=0, sticky="nsew", pady=(0, 6))
        f.grid_columnconfigure(0, weight=1)
        f.grid_rowconfigure(0, weight=1)
        self.scroll.grid_rowconfigure(start + 1, weight=1)

        header = ctk.CTkFrame(f, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew")
        header.grid_columnconfigure(0, weight=1)
        ctk.CTkButton(header, text="+ 添加视频文件", width=110, height=28, command=self._add_file).grid(row=0, column=0, padx=10, pady=6, sticky="w")

        self.list_frame = ctk.CTkScrollableFrame(f)
        self.list_frame.grid(row=1, column=0, sticky="nsew", padx=5, pady=(0, 5))
        self.list_frame.grid_columnconfigure(1, weight=1)

    def _add_file(self) -> None:
        paths = filedialog.askopenfilenames(filetypes=[("Video files", "*.mp4 *.mov *.mkv")])
        for p in paths:
            path = Path(p).resolve()
            if path not in self._file_paths:
                self._file_paths.append(path)
        self._refresh_list()

    def _refresh_list(self) -> None:
        for w in self.list_frame.winfo_children():
            w.destroy()

        for idx, path in enumerate(self._file_paths):
            item = ctk.CTkFrame(self.list_frame)
            item.grid(row=idx, column=0, sticky="ew", pady=2)
            item.grid_columnconfigure(1, weight=1)

            ctk.CTkLabel(item, text=f"{idx+1}.", width=24, font=ctk.CTkFont(size=11)).grid(row=0, column=0, padx=(8, 2))
            ctk.CTkLabel(item, text=path.name, anchor="w", font=ctk.CTkFont(size=11)).grid(row=0, column=1, sticky="ew", padx=4)
            ctk.CTkLabel(item, text=str(path.parent), anchor="w", font=ctk.CTkFont(size=9),
                         text_color=("gray40", "gray60")).grid(row=0, column=2, sticky="w", padx=4)

            btn_f = ctk.CTkFrame(item, fg_color="transparent")
            btn_f.grid(row=0, column=3, padx=4)
            for i, (t, cmd) in enumerate([("▲", lambda i=idx: self._move_up(i)),
                                           ("▼", lambda i=idx: self._move_down(i)),
                                           ("✕", lambda i=idx: self._remove_file(i))]):
                b = ctk.CTkButton(btn_f, text=t, width=26, height=22, command=cmd, font=ctk.CTkFont(size=10))
                b.grid(row=0, column=i, padx=1)
                if t == "✕":
                    b.configure(fg_color="#b03a2e", hover_color="#c0392b")
                elif (t == "▲" and idx == 0) or (t == "▼" and idx == len(self._file_paths) - 1):
                    b.configure(state="disabled")

        if not self._file_paths:
            ctk.CTkLabel(self.list_frame, text="（尚未添加文件）", text_color=("gray50", "gray40"),
                         font=ctk.CTkFont(size=11)).grid(row=0, column=0, padx=10, pady=20)

    def _move_up(self, idx: int) -> None:
        if idx > 0:
            self._file_paths[idx], self._file_paths[idx - 1] = self._file_paths[idx - 1], self._file_paths[idx]
            self._refresh_list()

    def _move_down(self, idx: int) -> None:
        if idx < len(self._file_paths) - 1:
            self._file_paths[idx], self._file_paths[idx + 1] = self._file_paths[idx + 1], self._file_paths[idx]
            self._refresh_list()

    def _remove_file(self, idx: int) -> None:
        if 0 <= idx < len(self._file_paths):
            self._file_paths.pop(idx)
            self._refresh_list()

    def _build_output_section(self) -> None:
        start = self.scroll.grid_size()[1]
        _section_header(self.scroll, "输出").grid(row=start, column=0, sticky="ew")
        f = ctk.CTkFrame(self.scroll)
        f.grid(row=start + 1, column=0, sticky="ew", pady=(0, 6))
        f.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(f, text="输出路径:").grid(row=0, column=0, padx=(15, 5), pady=(10, 4), sticky="w")
        self.output_entry = ctk.CTkEntry(f, placeholder_text="选择合并后的文件保存路径...")
        self.output_entry.grid(row=0, column=1, sticky="ew", padx=5, pady=(10, 4))
        _browse_button(f, "浏览", self._browse_output).grid(row=0, column=2, padx=(5, 15), pady=(10, 4))

        self.overwrite_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(f, text="覆盖已有文件", variable=self.overwrite_var).grid(row=1, column=0, columnspan=2, padx=(15, 5), pady=(0, 8), sticky="w")

    def _browse_output(self) -> None:
        p = filedialog.asksaveasfilename(defaultextension=".mp4", filetypes=[("MP4", "*.mp4")])
        if p:
            self.output_entry.delete(0, "end")
            self.output_entry.insert(0, p)

    def _build_action_section(self) -> None:
        start = self.scroll.grid_size()[1]
        f = ctk.CTkFrame(self.scroll, fg_color="transparent")
        f.grid(row=start, column=0, sticky="ew", pady=(4, 0))
        f.grid_columnconfigure(0, weight=1)

        self.run_btn = ctk.CTkButton(f, text="加入队列", command=self._run, height=34,
                                     font=ctk.CTkFont(size=13), width=120)
        self.run_btn.grid(row=0, column=0, padx=15, pady=8, sticky="w")
        self.stop_btn = ctk.CTkButton(f, text="停止", command=self._stop, state="disabled",
                                      fg_color="#c0392b", hover_color="#e74c3c",
                                      height=34, width=80)
        self.stop_btn.grid(row=0, column=0, padx=15, pady=8, sticky="w")
        self.stop_btn.grid_remove()

    def _build_log_section(self) -> None:
        start = self.scroll.grid_size()[1]
        _section_header(self.scroll, "日志").grid(row=start, column=0, sticky="ew")
        f = ctk.CTkFrame(self.scroll)
        f.grid(row=start + 1, column=0, sticky="nsew", pady=(0, 6))
        f.grid_columnconfigure(0, weight=1)
        f.grid_rowconfigure(0, weight=1)
        self.scroll.grid_rowconfigure(start + 1, weight=1)

        self.log_viewer = LogViewer(f)
        self.log_viewer.grid(row=0, column=0, sticky="nsew")

    def _run(self) -> None:
        if len(self._file_paths) < 2:
            self.log_viewer.clear()
            self.log_viewer.append("请至少添加 2 个视频文件。")
            return

        output_str = self.output_entry.get().strip()
        if not output_str:
            self.log_viewer.clear()
            self.log_viewer.append("请指定输出路径。")
            return

        output_path = Path(output_str).expanduser().resolve()
        task = self.task_queue.enqueue(
            f"合并 {len(self._file_paths)} 个视频",
            run_merge,
            args=(self._file_paths[:], output_path, self.overwrite_var.get()),
            result_paths=[output_path],
        )
        self.log_viewer.clear()
        self.log_viewer.append(f"已加入任务队列: #{task.id} {task.title}")

    def _stop(self) -> None:
        if self.worker is not None:
            self.worker.cancel()
        self.stop_btn.configure(state="disabled", text="停止中...")

    def _poll_log_queue(self) -> None:
        try:
            while True:
                msg = self.log_queue.get_nowait()
                self.log_viewer.append(msg)
        except queue.Empty:
            pass
        if self._running and self.worker is not None and self.worker.done_event.is_set():
            self._on_done()
            return
        if self._running:
            self._poll_job = self.tab.after(_POLL_INTERVAL, self._poll_log_queue)

    def _on_done(self) -> None:
        self._running = False
        self._poll_log_queue()
        self._reset_buttons()

    def _reset_buttons(self) -> None:
        self.worker = None
        self.stop_btn.configure(state="normal", text="停止")
        self.stop_btn.grid_remove()
        self.run_btn.grid()
