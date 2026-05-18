from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from ..models import AnalysisResult, AppConfig


class EditorBackend(ABC):
    name = "base"

    @abstractmethod
    def analyze(self, source_path: Path, config: AppConfig) -> AnalysisResult:
        raise NotImplementedError

    @abstractmethod
    def render(self, source_path: Path, output_path: Path, config: AppConfig) -> None:
        raise NotImplementedError
