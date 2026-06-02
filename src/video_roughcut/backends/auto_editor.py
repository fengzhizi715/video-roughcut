from __future__ import annotations

import json
import math
import re
import subprocess
from pathlib import Path

from .base import EditorBackend
from ..models import AnalysisResult, AppConfig, RemovedSegment


class BackendError(RuntimeError):
    """Raised when backend analysis or rendering fails."""


class AutoEditorBackend(EditorBackend):
    name = "auto-editor"

    def analyze(self, source_path: Path, config: AppConfig) -> AnalysisResult:
        original_duration = self._probe_duration(source_path)
        silences = self._detect_silences(source_path, config)
        removed_segments = compress_silences(
            silences=silences,
            total_duration=original_duration,
            padding_before=config.padding_before,
            padding_after=config.padding_after,
            min_silence_duration=config.min_silence_duration,
            min_clip_duration=config.min_clip_duration,
        )
        return AnalysisResult(
            source_path=source_path,
            detected_silences=silences,
            removed_segments=removed_segments,
            original_duration=original_duration,
            output_duration=max(0.0, original_duration - sum(s.duration for s in removed_segments)),
        )

    def render(self, source_path: Path, output_path: Path, config: AppConfig) -> None:
        command = build_render_command(source_path, output_path, config)
        print(f"[render] {' '.join(command)}")
        completed = subprocess.run(command, capture_output=True, text=True)
        if completed.returncode != 0:
            raise BackendError(
                "auto-editor render failed.\n"
                f"Command: {' '.join(command)}\n"
                f"stderr: {completed.stderr.strip() or '(empty)'}"
            )

    def _probe_duration(self, source_path: Path) -> float:
        command = [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "json",
            str(source_path),
        ]
        completed = subprocess.run(command, capture_output=True, text=True)
        if completed.returncode != 0:
            raise BackendError(f"ffprobe failed for {source_path}: {completed.stderr.strip()}")
        payload = json.loads(completed.stdout)
        duration = float(payload["format"]["duration"])
        return duration

    def _detect_silences(self, source_path: Path, config: AppConfig) -> list[RemovedSegment]:
        command = [
            "ffmpeg",
            "-hide_banner",
            "-i",
            str(source_path),
            "-af",
            (
                "silencedetect="
                f"noise={config.silence_threshold}dB:"
                f"d={config.min_silence_duration}"
            ),
            "-f",
            "null",
            "-",
        ]
        completed = subprocess.run(command, capture_output=True, text=True)
        raw_output = f"{completed.stdout}\n{completed.stderr}"
        if completed.returncode not in (0, 255):
            raise BackendError(f"ffmpeg silencedetect failed for {source_path}: {completed.stderr.strip()}")
        return parse_silencedetect_output(raw_output)


def db_to_ratio(decibels: float) -> float:
    return math.pow(10, decibels / 20.0)


def build_render_command(source_path: Path, output_path: Path, config: AppConfig) -> list[str]:
    threshold_ratio = db_to_ratio(config.silence_threshold)
    return [
        "auto-editor",
        str(source_path),
        "--edit",
        f"audio:threshold={threshold_ratio:.6f}",
        "--margin",
        f"{config.padding_before}s,{config.padding_after}s",
        "--smooth",
        f"{config.min_silence_duration}s,{config.min_clip_duration}s",
        "--when-inactive",
        "cut",
        "--when-active",
        "nil",
        "--video-codec",
        config.video_codec,
        "--audio-codec",
        config.audio_codec,
        "-crf",
        str(config.video_crf),
        "--preset",
        config.video_preset,
        "--audio-bitrate",
        config.audio_bitrate,
        "--no-open",
        "-o",
        str(output_path),
    ]


def parse_silencedetect_output(output: str) -> list[RemovedSegment]:
    starts: list[float] = []
    segments: list[RemovedSegment] = []
    start_pattern = re.compile(r"silence_start:\s*([0-9.]+)")
    end_pattern = re.compile(r"silence_end:\s*([0-9.]+)\s*\|\s*silence_duration:\s*([0-9.]+)")
    for line in output.splitlines():
        start_match = start_pattern.search(line)
        if start_match:
            starts.append(float(start_match.group(1)))
            continue
        end_match = end_pattern.search(line)
        if end_match and starts:
            start = starts.pop(0)
            end = float(end_match.group(1))
            duration = float(end_match.group(2))
            segments.append(RemovedSegment(start=start, end=end, duration=duration))
    return segments


def compress_silences(
    silences: list[RemovedSegment],
    total_duration: float,
    padding_before: float,
    padding_after: float,
    min_silence_duration: float,
    min_clip_duration: float,
) -> list[RemovedSegment]:
    if not silences:
        return []

    padded: list[tuple[float, float]] = []
    for silence in silences:
        if silence.duration < min_silence_duration:
            continue
        start = max(0.0, silence.start + padding_before)
        end = min(total_duration, silence.end - padding_after)
        if end - start <= 0:
            continue
        padded.append((start, end))

    if not padded:
        return []

    merged: list[list[float]] = [[padded[0][0], padded[0][1]]]
    for start, end in padded[1:]:
        last = merged[-1]
        if start <= last[1]:
            last[1] = max(last[1], end)
        else:
            merged.append([start, end])

    filtered: list[RemovedSegment] = []
    cursor = 0.0
    for start, end in merged:
        if start - cursor < min_clip_duration:
            continue
        filtered.append(RemovedSegment(start=start, end=end, duration=end - start))
        cursor = end
    return filtered
