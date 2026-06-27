from __future__ import annotations

import customtkinter as ctk

from .presets import PresetStore
from .task_queue import TaskQueue
from .tabs.queue_tab import QueueTab
from .tabs.rough_cut_tab import RoughCutTab
from .tabs.merge_tab import MergeTab
from .tabs.split_tab import SplitTab


class App(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()

        self.title("Video Roughcut")
        self.geometry("860x720")
        self.minsize(720, 560)

        ctk.set_appearance_mode("system")
        ctk.set_default_color_theme("blue")

        self.tab_view = ctk.CTkTabview(self, corner_radius=6)
        self.tab_view.pack(fill="both", expand=True, padx=12, pady=12)

        task_queue = TaskQueue()
        preset_store = PresetStore()

        RoughCutTab(self.tab_view, "  粗剪  ", task_queue, preset_store)
        MergeTab(self.tab_view, "  合并  ", task_queue)
        SplitTab(self.tab_view, "  拆分  ", task_queue)
        QueueTab(self.tab_view, "  任务队列  ", task_queue)


def main() -> None:
    app = App()
    app.mainloop()
