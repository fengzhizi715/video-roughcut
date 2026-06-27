from __future__ import annotations

import queue

import customtkinter as ctk

from ..task_queue import QueuedTask, TaskQueue, TaskStatus, open_path
from ..workers import _POLL_INTERVAL
from ..widgets.log_viewer import LogViewer


STATUS_LABELS = {
    TaskStatus.QUEUED: "等待中",
    TaskStatus.RUNNING: "运行中",
    TaskStatus.COMPLETED: "已完成",
    TaskStatus.FAILED: "失败",
    TaskStatus.CANCELLED: "已取消",
}


class QueueTab:
    def __init__(self, tabview: ctk.CTkTabview, name: str, task_queue: TaskQueue) -> None:
        self.tab = tabview.add(name)
        self.task_queue = task_queue
        self._rendered_state: tuple[tuple[int, str], ...] = ()
        self._log_task_id: int | None = None

        self.tab.grid_columnconfigure(0, weight=1)
        self.tab.grid_rowconfigure(1, weight=1)
        self.tab.grid_rowconfigure(3, weight=1)

        self._build_actions()
        self._build_task_list()
        self._build_log()
        self._poll()

    def _build_actions(self) -> None:
        actions = ctk.CTkFrame(self.tab, fg_color="transparent")
        actions.grid(row=0, column=0, sticky="ew", padx=12, pady=(12, 4))
        actions.grid_columnconfigure(0, weight=1)

        self.summary_label = ctk.CTkLabel(actions, text="暂无任务", anchor="w")
        self.summary_label.grid(row=0, column=0, sticky="w")

        self.cancel_btn = ctk.CTkButton(actions, text="停止当前任务", width=110, command=self._cancel_current)
        self.cancel_btn.grid(row=0, column=1, padx=6)

        self.clear_btn = ctk.CTkButton(actions, text="清理已完成", width=100, command=self._clear_finished)
        self.clear_btn.grid(row=0, column=2, padx=(6, 0))

    def _build_task_list(self) -> None:
        self.task_list = ctk.CTkScrollableFrame(self.tab)
        self.task_list.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 8))
        self.task_list.grid_columnconfigure(0, weight=1)

    def _build_log(self) -> None:
        ctk.CTkLabel(self.tab, text="当前任务日志", font=ctk.CTkFont(size=13, weight="bold")).grid(
            row=2, column=0, sticky="w", padx=16
        )
        self.log_viewer = LogViewer(self.tab)
        self.log_viewer.grid(row=3, column=0, sticky="nsew", padx=12, pady=(4, 12))

    def _poll(self) -> None:
        self._drain_current_log()
        self.task_queue.tick()
        self._drain_current_log()
        self._refresh_if_needed()
        self.cancel_btn.configure(state="normal" if self.task_queue.current else "disabled")
        self.tab.after(_POLL_INTERVAL, self._poll)

    def _drain_current_log(self) -> None:
        task = self.task_queue.current
        if task is None:
            return
        if self._log_task_id != task.id:
            self.log_viewer.clear()
            self._log_task_id = task.id
        try:
            while True:
                self.log_viewer.append(task.log_queue.get_nowait())
        except queue.Empty:
            pass

    def _refresh_if_needed(self) -> None:
        state = tuple((task.id, task.status.value) for task in self.task_queue.tasks)
        if state == self._rendered_state:
            return
        self._rendered_state = state
        self._render_tasks()

    def _render_tasks(self) -> None:
        for child in self.task_list.winfo_children():
            child.destroy()

        total = len(self.task_queue.tasks)
        running = sum(1 for task in self.task_queue.tasks if task.status == TaskStatus.RUNNING)
        queued = sum(1 for task in self.task_queue.tasks if task.status == TaskStatus.QUEUED)
        self.summary_label.configure(text=f"任务 {total} 个，运行 {running} 个，等待 {queued} 个")

        if not self.task_queue.tasks:
            ctk.CTkLabel(self.task_list, text="还没有任务，去粗剪/合并/拆分页加入一个。", text_color=("gray50", "gray40")).grid(
                row=0, column=0, padx=12, pady=24
            )
            return

        for row, task in enumerate(self.task_queue.tasks):
            self._render_task(row, task)

    def _render_task(self, row: int, task: QueuedTask) -> None:
        item = ctk.CTkFrame(self.task_list)
        item.grid(row=row, column=0, sticky="ew", pady=3)
        item.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(item, text=f"#{task.id}", width=36).grid(row=0, column=0, padx=(8, 4), pady=8)
        ctk.CTkLabel(item, text=task.title, anchor="w").grid(row=0, column=1, sticky="ew", padx=4)
        ctk.CTkLabel(item, text=STATUS_LABELS[task.status], width=70).grid(row=0, column=2, padx=4)

        if task.status == TaskStatus.COMPLETED and task.result_paths:
            ctk.CTkButton(item, text="打开", width=60, command=lambda task=task: self._open_first_result(task)).grid(
                row=0, column=3, padx=(4, 8), pady=6
            )

        if task.error_message:
            ctk.CTkLabel(item, text=task.error_message, text_color="#c0392b", anchor="w").grid(
                row=1, column=1, columnspan=3, sticky="ew", padx=4, pady=(0, 8)
            )

    def _open_first_result(self, task: QueuedTask) -> None:
        if task.result_paths:
            open_path(task.result_paths[0])

    def _cancel_current(self) -> None:
        self.task_queue.cancel_current()

    def _clear_finished(self) -> None:
        self.task_queue.clear_finished()
        if self.task_queue.current is None:
            self._log_task_id = None
            self.log_viewer.clear()
        self._rendered_state = ()
        self._render_tasks()
