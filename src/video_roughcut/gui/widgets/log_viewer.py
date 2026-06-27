from __future__ import annotations

import customtkinter as ctk


class LogViewer(ctk.CTkFrame):
    def __init__(self, parent: ctk.CTk | ctk.CTkFrame, **kwargs) -> None:
        super().__init__(parent, **kwargs)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.text = ctk.CTkTextbox(self, state="disabled", wrap="word", font=("Menlo", 11))
        self.text.grid(row=0, column=0, sticky="nsew")

    def append(self, line: str) -> None:
        self.text.configure(state="normal")
        self.text.insert("end", line + "\n")
        self.text.see("end")
        self.text.configure(state="disabled")

    def clear(self) -> None:
        self.text.configure(state="normal")
        self.text.delete("0.0", "end")
        self.text.configure(state="disabled")
