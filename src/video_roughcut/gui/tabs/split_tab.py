from __future__ import annotations

import queue
from pathlib import Path

import customtkinter as ctk
from tkinter import filedialog

from ..task_queue import TaskQueue
from ..workers import LogQueue, WorkerController, _POLL_INTERVAL
from ..workers.split_worker import run_split
from ..widgets.log_viewer import LogViewer
from ...split import parse_time, _auto_output_path


def _section_header(parent: ctk.CTkFrame | ctk.CTkScrollableFrame, text: str) -> ctk.CTkFrame:
    h = ctk.CTkFrame(parent, fg_color="transparent")
    h.grid_columnconfigure(0, weight=1)
    ctk.CTkLabel(h, text=text, font=ctk.CTkFont(size=13, weight="bold"), anchor="w").grid(row=0, column=0, sticky="w", padx=4, pady=(6, 2))
    ctk.CTkFrame(h, height=1, fg_color=("gray70", "gray30")).grid(row=1, column=0, sticky="ew", padx=4)
    return h


def _browse_button(parent, text, command) -> ctk.CTkButton:
    return ctk.CTkButton(parent, text=text, width=60, height=28, command=command)


class SplitTab:
    def __init__(self, tabview: ctk.CTkTabview, name: str, task_queue: TaskQueue) -> None:
        self.tab = tabview.add(name)
        self.task_queue = task_queue
        self.log_queue = LogQueue()
        self.worker: WorkerController | None = None
        self._running = False
        self._poll_job: str | None = None

        self.tab.grid_columnconfigure(0, weight=1)
        self.tab.grid_rowconfigure(0, weight=1)

        self.scroll = ctk.CTkScrollableFrame(self.tab)
        self.scroll.grid(row=0, column=0, sticky="nsew")
        self.scroll.grid_columnconfigure(0, weight=1)

        self._build_input_section()
        self._build_time_section()
        self._build_output_section()
        self._build_action_section()
        self._build_log_section()

    def _build_input_section(self) -> None:
        start = self.scroll.grid_size()[1]
        _section_header(self.scroll, "输入视频").grid(row=start, column=0, sticky="ew")
        f = ctk.CTkFrame(self.scroll)
        f.grid(row=start + 1, column=0, sticky="ew", pady=(0, 6))
        f.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(f, text="视频文件:").grid(row=0, column=0, padx=(15, 5), pady=10, sticky="w")
        self.input_entry = ctk.CTkEntry(f, placeholder_text="选择要拆分的视频文件...")
        self.input_entry.grid(row=0, column=1, sticky="ew", padx=5, pady=10)
        _browse_button(f, "浏览", self._browse_input).grid(row=0, column=2, padx=(5, 15), pady=10)

    def _browse_input(self) -> None:
        p = filedialog.askopenfilename(filetypes=[("Video files", "*.mp4 *.mov *.mkv")])
        if p:
            self.input_entry.delete(0, "end")
            self.input_entry.insert(0, p)

    def _build_time_section(self) -> None:
        start = self.scroll.grid_size()[1]
        _section_header(self.scroll, "时间参数").grid(row=start, column=0, sticky="ew")
        f = ctk.CTkFrame(self.scroll)
        f.grid(row=start + 1, column=0, sticky="ew", pady=(0, 6))
        f.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(f, text="起始时间:").grid(row=0, column=0, padx=(15, 5), pady=(10, 4), sticky="w")
        self.start_entry = ctk.CTkEntry(f, placeholder_text="0 或 00:00:00.000")
        self.start_entry.insert(0, "0")
        self.start_entry.grid(row=0, column=1, sticky="ew", padx=5, pady=(10, 4))

        self.end_radio_var = ctk.StringVar(value="end")
        r1 = ctk.CTkRadioButton(f, text="结束时间:", variable=self.end_radio_var, value="end")
        r1.grid(row=1, column=0, padx=(15, 5), pady=4, sticky="w")
        self.end_entry = ctk.CTkEntry(f, placeholder_text="HH:MM:SS.mmm 或秒数")
        self.end_entry.grid(row=1, column=1, sticky="ew", padx=5, pady=4)

        r2 = ctk.CTkRadioButton(f, text="时长 (秒):", variable=self.end_radio_var, value="duration")
        r2.grid(row=2, column=0, padx=(15, 5), pady=4, sticky="w")
        self.duration_entry = ctk.CTkEntry(f, placeholder_text="秒数")
        self.duration_entry.grid(row=2, column=1, sticky="ew", padx=5, pady=4)

    def _build_output_section(self) -> None:
        start = self.scroll.grid_size()[1]
        _section_header(self.scroll, "输出").grid(row=start, column=0, sticky="ew")
        f = ctk.CTkFrame(self.scroll)
        f.grid(row=start + 1, column=0, sticky="ew", pady=(0, 6))
        f.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(f, text="输出路径:").grid(row=0, column=0, padx=(15, 5), pady=(10, 4), sticky="w")
        self.output_entry = ctk.CTkEntry(f, placeholder_text="留空则自动生成")
        self.output_entry.grid(row=0, column=1, sticky="ew", padx=5, pady=(10, 4))
        _browse_button(f, "浏览", self._browse_output).grid(row=0, column=2, padx=(5, 15), pady=(10, 4))

        cb_f = ctk.CTkFrame(f, fg_color="transparent")
        cb_f.grid(row=1, column=0, columnspan=3, sticky="w", padx=12, pady=(0, 8))
        self.reencode_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(cb_f, text="帧精确模式（--reencode）", variable=self.reencode_var).grid(row=0, column=0, padx=3)
        self.overwrite_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(cb_f, text="覆盖已有文件", variable=self.overwrite_var).grid(row=0, column=1, padx=15)

    def _browse_output(self) -> None:
        p = filedialog.asksaveasfilename(defaultextension=".mp4",
                                          filetypes=[("MP4", "*.mp4"), ("MOV", "*.mov"), ("MKV", "*.mkv")])
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
        try:
            input_path = Path(self.input_entry.get()).expanduser().resolve()
            start_time = parse_time(self.start_entry.get())

            if self.end_radio_var.get() == "end":
                end_time = parse_time(self.end_entry.get())
                duration = end_time - start_time
                if duration <= 0:
                    raise ValueError("结束时间必须晚于起始时间。")
            else:
                duration = float(self.duration_entry.get())
                end_time = start_time + duration

            if duration <= 0:
                raise ValueError("时长必须大于 0。")

            output_path_str = self.output_entry.get().strip()
            output_path = Path(output_path_str).expanduser().resolve() if output_path_str else _auto_output_path(input_path, start_time, end_time)

        except ValueError as exc:
            self.log_viewer.clear()
            self.log_viewer.append(f"输入错误: {exc}")
            return

        task = self.task_queue.enqueue(
            f"拆分 {input_path.name}",
            run_split,
            args=(input_path, output_path, start_time, duration, self.reencode_var.get(), self.overwrite_var.get()),
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
