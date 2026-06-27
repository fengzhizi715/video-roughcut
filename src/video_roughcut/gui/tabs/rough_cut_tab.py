from __future__ import annotations

import queue
from pathlib import Path

import customtkinter as ctk
from tkinter import filedialog, simpledialog

from ..presets import PresetStore, RoughCutPreset
from ..task_queue import TaskQueue
from ..workers import LogQueue, WorkerController, _POLL_INTERVAL
from ..workers.rough_cut_worker import run_rough_cut
from ..widgets.log_viewer import LogViewer


QUALITY_PROFILES = ["high", "standard"]
SECTION_PAD = (0, 6)


def _section_header(parent: ctk.CTkFrame | ctk.CTkScrollableFrame, text: str) -> ctk.CTkFrame:
    h = ctk.CTkFrame(parent, fg_color="transparent")
    h.grid_columnconfigure(0, weight=1)
    ctk.CTkLabel(h, text=text, font=ctk.CTkFont(size=13, weight="bold"), anchor="w").grid(row=0, column=0, sticky="w", padx=4, pady=(6, 2))
    ctk.CTkFrame(h, height=1, fg_color=("gray70", "gray30")).grid(row=1, column=0, sticky="ew", padx=4)
    return h


def _param_row(parent: ctk.CTkFrame | ctk.CTkScrollableFrame, row: int,
               items: list[tuple[str, ctk.CTkEntry]]) -> None:
    for col, (label, entry) in enumerate(items):
        ctk.CTkLabel(parent, text=label).grid(row=row * 2, column=col, sticky="w", padx=(10 if col == 0 else 5, 2), pady=(8, 0))
        entry.grid(row=row * 2 + 1, column=col, sticky="ew", padx=(10 if col == 0 else 5, 10), pady=(0, 4))


def _browse_button(parent: ctk.CTkFrame | ctk.CTkScrollableFrame, text: str, command, **kwargs) -> ctk.CTkButton:
    return ctk.CTkButton(parent, text=text, width=60, height=28, command=command, **kwargs)


class RoughCutTab:
    def __init__(self, tabview: ctk.CTkTabview, name: str, task_queue: TaskQueue, preset_store: PresetStore) -> None:
        self.tab = tabview.add(name)
        self.task_queue = task_queue
        self.preset_store = preset_store
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
        self._build_silence_section()
        self._build_quality_section()
        self._build_preset_section()
        self._build_output_section()
        self._build_action_section()
        self._build_log_section()

    # --------------- input ---------------
    def _build_input_section(self) -> None:
        start = self.scroll.grid_size()[1]
        _section_header(self.scroll, "输入").grid(row=start, column=0, sticky="ew")
        f = ctk.CTkFrame(self.scroll)
        f.grid(row=start + 1, column=0, sticky="ew", pady=SECTION_PAD)
        f.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(f, text="视频或目录:").grid(row=0, column=0, padx=(15, 5), pady=10, sticky="w")
        self.input_entry = ctk.CTkEntry(f, placeholder_text="选择视频文件或包含视频的目录...")
        self.input_entry.grid(row=0, column=1, sticky="ew", padx=5, pady=10)
        bb = ctk.CTkFrame(f, fg_color="transparent")
        bb.grid(row=0, column=2, padx=(5, 15), pady=10)
        _browse_button(bb, "  文件  ", self._browse_file).grid(row=0, column=0, padx=2)
        _browse_button(bb, "  目录  ", self._browse_dir).grid(row=0, column=1, padx=2)

    def _browse_file(self) -> None:
        p = filedialog.askopenfilename(filetypes=[("Video files", "*.mp4 *.mov *.mkv")])
        if p:
            self.input_entry.delete(0, "end")
            self.input_entry.insert(0, p)

    def _browse_dir(self) -> None:
        p = filedialog.askdirectory()
        if p:
            self.input_entry.delete(0, "end")
            self.input_entry.insert(0, p)

    # --------------- silence ---------------
    def _build_silence_section(self) -> None:
        start = self.scroll.grid_size()[1]
        _section_header(self.scroll, "静音检测参数").grid(row=start, column=0, sticky="ew")
        f = ctk.CTkFrame(self.scroll)
        f.grid(row=start + 1, column=0, sticky="ew", pady=SECTION_PAD)
        for i in range(5):
            f.grid_columnconfigure(i, weight=1)

        self.threshold_entry = ctk.CTkEntry(f)
        self.threshold_entry.insert(0, "-35")
        self.min_sil_entry = ctk.CTkEntry(f)
        self.min_sil_entry.insert(0, "0.6")
        self.pad_before_entry = ctk.CTkEntry(f)
        self.pad_before_entry.insert(0, "0.25")
        self.pad_after_entry = ctk.CTkEntry(f)
        self.pad_after_entry.insert(0, "0.25")
        self.min_clip_entry = ctk.CTkEntry(f)
        self.min_clip_entry.insert(0, "0.5")

        _param_row(f, 0, [
            ("静音阈值 (dB)", self.threshold_entry),
            ("最小时长 (s)", self.min_sil_entry),
            ("Padding 前 (s)", self.pad_before_entry),
            ("Padding 后 (s)", self.pad_after_entry),
            ("最短片段 (s)", self.min_clip_entry),
        ])

    # --------------- quality ---------------
    def _build_quality_section(self) -> None:
        start = self.scroll.grid_size()[1]
        _section_header(self.scroll, "输出质量").grid(row=start, column=0, sticky="ew")
        f = ctk.CTkFrame(self.scroll)
        f.grid(row=start + 1, column=0, sticky="ew", pady=SECTION_PAD)
        f.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(f, text="预设:").grid(row=0, column=0, padx=(15, 5), pady=(10, 5), sticky="w")
        self.quality_menu = ctk.CTkOptionMenu(f, values=QUALITY_PROFILES, command=self._on_quality_change, width=120)
        self.quality_menu.set("high")
        self.quality_menu.grid(row=0, column=1, padx=5, pady=(10, 5), sticky="w")

        self.advanced_btn = ctk.CTkButton(f, text="高级参数 ▾", fg_color="transparent",
                                          text_color=("gray20", "gray80"), hover=False,
                                          width=100, height=24, command=self._toggle_advanced)
        self.advanced_btn.grid(row=0, column=2, padx=10, pady=(10, 5), sticky="e")

        self.advanced_frame = ctk.CTkFrame(f, fg_color="transparent")
        self.advanced_frame.grid(row=1, column=0, columnspan=3, sticky="ew", padx=5)
        for i in range(5):
            self.advanced_frame.grid_columnconfigure(i, weight=1)

        self.advanced_visible = False
        self._build_advanced_fields()

    def _build_advanced_fields(self) -> None:
        self.vcodec_entry = ctk.CTkEntry(self.advanced_frame)
        self.vcodec_entry.insert(0, "libx264")
        self.crf_entry = ctk.CTkEntry(self.advanced_frame)
        self.crf_entry.insert(0, "18")
        self.preset_entry = ctk.CTkEntry(self.advanced_frame)
        self.preset_entry.insert(0, "slow")
        self.bitrate_entry = ctk.CTkEntry(self.advanced_frame)
        self.bitrate_entry.insert(0, "192k")
        self.acodec_entry = ctk.CTkEntry(self.advanced_frame)
        self.acodec_entry.insert(0, "aac")

        _param_row(self.advanced_frame, 0, [
            ("视频编码器", self.vcodec_entry),
            ("CRF", self.crf_entry),
            ("编码预设", self.preset_entry),
            ("音频码率", self.bitrate_entry),
            ("音频编码器", self.acodec_entry),
        ])
        self.advanced_frame.grid_remove()

    def _build_preset_section(self) -> None:
        start = self.scroll.grid_size()[1]
        _section_header(self.scroll, "参数预设").grid(row=start, column=0, sticky="ew")
        f = ctk.CTkFrame(self.scroll)
        f.grid(row=start + 1, column=0, sticky="ew", pady=SECTION_PAD)
        f.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(f, text="预设:").grid(row=0, column=0, padx=(15, 5), pady=10, sticky="w")
        self.preset_menu = ctk.CTkOptionMenu(f, values=self.preset_store.names(), width=160)
        if self.preset_store.names():
            self.preset_menu.set("high" if "high" in self.preset_store.names() else self.preset_store.names()[0])
        self.preset_menu.grid(row=0, column=1, sticky="w", padx=5, pady=10)
        ctk.CTkButton(f, text="应用", width=70, command=self._apply_selected_preset).grid(row=0, column=2, padx=5, pady=10)
        ctk.CTkButton(f, text="保存当前", width=90, command=self._save_current_preset).grid(row=0, column=3, padx=(5, 15), pady=10)

    def _toggle_advanced(self) -> None:
        if self.advanced_visible:
            self.advanced_frame.grid_remove()
            self.advanced_btn.configure(text="高级参数 ▸")
        else:
            self.advanced_frame.grid()
            self.advanced_btn.configure(text="高级参数 ▾")
        self.advanced_visible = not self.advanced_visible

    def _on_quality_change(self, profile: str) -> None:
        presets = {
            "high": {"vcodec": "libx264", "acodec": "aac", "crf": "18", "preset": "slow", "bitrate": "192k"},
            "standard": {"vcodec": "libx264", "acodec": "aac", "crf": "23", "preset": "medium", "bitrate": "128k"},
        }
        p = presets.get(profile, presets["high"])
        mapping = {"vcodec": self.vcodec_entry, "acodec": self.acodec_entry,
                   "crf": self.crf_entry, "preset": self.preset_entry, "bitrate": self.bitrate_entry}
        for k, entry in mapping.items():
            entry.delete(0, "end")
            entry.insert(0, p[k])

    def _apply_selected_preset(self) -> None:
        preset = self.preset_store.get(self.preset_menu.get())
        self._set_entry(self.threshold_entry, str(preset.silence_threshold))
        self._set_entry(self.min_sil_entry, str(preset.min_silence_duration))
        self._set_entry(self.pad_before_entry, str(preset.padding_before))
        self._set_entry(self.pad_after_entry, str(preset.padding_after))
        self._set_entry(self.min_clip_entry, str(preset.min_clip_duration))
        self.quality_menu.set(preset.quality_profile)
        self._set_entry(self.vcodec_entry, preset.video_codec)
        self._set_entry(self.acodec_entry, preset.audio_codec)
        self._set_entry(self.crf_entry, str(preset.video_crf))
        self._set_entry(self.preset_entry, preset.video_preset)
        self._set_entry(self.bitrate_entry, preset.audio_bitrate)
        self._set_entry(self.suffix_entry, preset.output_suffix)

    def _save_current_preset(self) -> None:
        name = simpledialog.askstring("保存预设", "预设名称:", parent=self.tab)
        if not name:
            return
        try:
            self.preset_store.save(name, self._current_preset())
        except ValueError as exc:
            self.log_viewer.clear()
            self.log_viewer.append(f"保存预设失败: {exc}")
            return
        values = self.preset_store.names()
        self.preset_menu.configure(values=values)
        self.preset_menu.set(name.strip())
        self.log_viewer.clear()
        self.log_viewer.append(f"已保存预设: {name.strip()}")

    def _current_preset(self) -> RoughCutPreset:
        return RoughCutPreset(
            silence_threshold=float(self.threshold_entry.get()),
            min_silence_duration=float(self.min_sil_entry.get()),
            padding_before=float(self.pad_before_entry.get()),
            padding_after=float(self.pad_after_entry.get()),
            min_clip_duration=float(self.min_clip_entry.get()),
            quality_profile=self.quality_menu.get(),
            video_codec=self.vcodec_entry.get().strip() or "libx264",
            audio_codec=self.acodec_entry.get().strip() or "aac",
            video_crf=int(self.crf_entry.get()),
            video_preset=self.preset_entry.get().strip() or "medium",
            audio_bitrate=self.bitrate_entry.get().strip() or "192k",
            output_suffix=self.suffix_entry.get().strip() or "_rough",
        )

    def _set_entry(self, entry: ctk.CTkEntry, value: str) -> None:
        entry.delete(0, "end")
        entry.insert(0, value)

    # --------------- output ---------------
    def _build_output_section(self) -> None:
        start = self.scroll.grid_size()[1]
        _section_header(self.scroll, "输出").grid(row=start, column=0, sticky="ew")
        f = ctk.CTkFrame(self.scroll)
        f.grid(row=start + 1, column=0, sticky="ew", pady=SECTION_PAD)
        f.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(f, text="输出目录:").grid(row=0, column=0, padx=(15, 5), pady=(10, 4), sticky="w")
        self.output_dir_entry = ctk.CTkEntry(f, placeholder_text="默认: outputs")
        self.output_dir_entry.grid(row=0, column=1, sticky="ew", padx=5, pady=(10, 4))
        _browse_button(f, "浏览", self._browse_output).grid(row=0, column=2, padx=(5, 15), pady=(10, 4))

        ctk.CTkLabel(f, text="后缀:").grid(row=1, column=0, padx=(15, 5), pady=4, sticky="w")
        self.suffix_entry = ctk.CTkEntry(f)
        self.suffix_entry.insert(0, "_rough")
        self.suffix_entry.grid(row=1, column=1, sticky="ew", padx=5, pady=4)

        cb_f = ctk.CTkFrame(f, fg_color="transparent")
        cb_f.grid(row=2, column=0, columnspan=3, sticky="w", padx=12, pady=(4, 8))
        self.overwrite_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(cb_f, text="覆盖已有文件", variable=self.overwrite_var).grid(row=0, column=0, padx=3)
        self.dry_run_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(cb_f, text="Dry-Run（仅分析不渲染）", variable=self.dry_run_var).grid(row=0, column=1, padx=15)

    def _browse_output(self) -> None:
        p = filedialog.askdirectory()
        if p:
            self.output_dir_entry.delete(0, "end")
            self.output_dir_entry.insert(0, p)

    # --------------- action ---------------
    def _build_action_section(self) -> None:
        start = self.scroll.grid_size()[1]
        f = ctk.CTkFrame(self.scroll, fg_color="transparent")
        f.grid(row=start, column=0, sticky="ew", pady=(4, 0))
        f.grid_columnconfigure(0, weight=1)

        self.run_btn = ctk.CTkButton(f, text="加入队列", command=self._run, height=34,
                                     font=ctk.CTkFont(size=13), width=140)
        self.run_btn.grid(row=0, column=0, padx=15, pady=8, sticky="w")
        self.stop_btn = ctk.CTkButton(f, text="停止", command=self._stop, state="disabled",
                                      fg_color="#c0392b", hover_color="#e74c3c",
                                      height=34, width=80)
        self.stop_btn.grid(row=0, column=0, padx=15, pady=8, sticky="w")
        self.stop_btn.grid_remove()

    # --------------- log ---------------
    def _build_log_section(self) -> None:
        start = self.scroll.grid_size()[1]
        _section_header(self.scroll, "日志").grid(row=start, column=0, sticky="ew")
        f = ctk.CTkFrame(self.scroll)
        f.grid(row=start + 1, column=0, sticky="nsew", pady=SECTION_PAD)
        f.grid_columnconfigure(0, weight=1)
        f.grid_rowconfigure(0, weight=1)
        self.scroll.grid_rowconfigure(start + 1, weight=1)

        self.log_viewer = LogViewer(f)
        self.log_viewer.grid(row=0, column=0, sticky="nsew")

    # --------------- run / stop / poll ---------------
    def _run(self) -> None:
        input_str = self.input_entry.get().strip()
        if not input_str:
            self.log_viewer.clear()
            self.log_viewer.append("请选择输入文件或目录。")
            return

        try:
            input_path = Path(input_str).expanduser().resolve()
            output_dir_str = self.output_dir_entry.get().strip()
            output_dir = Path(output_dir_str).expanduser().resolve() if output_dir_str else Path("outputs").resolve()
        except Exception as exc:
            self.log_viewer.clear()
            self.log_viewer.append(f"路径错误: {exc}")
            return

        try:
            silence_threshold = float(self.threshold_entry.get())
            min_silence_duration = float(self.min_sil_entry.get())
            padding_before = float(self.pad_before_entry.get())
            padding_after = float(self.pad_after_entry.get())
            min_clip_duration = float(self.min_clip_entry.get())
            video_crf = int(self.crf_entry.get())
        except ValueError as exc:
            self.log_viewer.clear()
            self.log_viewer.append(f"数字格式错误: {exc}")
            return

        task = self.task_queue.enqueue(
            f"粗剪 {input_path.name}",
            run_rough_cut,
            args=(input_path, output_dir, silence_threshold, min_silence_duration,
                  padding_before, padding_after, min_clip_duration,
                  self.quality_menu.get(),
                  self.vcodec_entry.get().strip() or "libx264",
                  self.acodec_entry.get().strip() or "aac",
                  video_crf, self.preset_entry.get().strip() or "medium",
                  self.bitrate_entry.get().strip() or "192k",
                  self.suffix_entry.get().strip() or "_rough",
                  self.overwrite_var.get(), self.dry_run_var.get()),
            result_paths=[output_dir],
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
