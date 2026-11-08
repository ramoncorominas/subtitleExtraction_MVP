from __future__ import annotations

from pathlib import Path
from typing import Any

from models.subtitle_item import SubtitleItem
from pipeline.io_utils import write_json, write_text


def format_timestamp_srt(seconds: float) -> str:
    total_ms = int(round(seconds * 1000))
    ms = total_ms % 1000
    total_seconds = total_ms // 1000
    s = total_seconds % 60
    total_minutes = total_seconds // 60
    m = total_minutes % 60
    h = total_minutes // 60
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def format_timestamp_vtt(seconds: float) -> str:
    return format_timestamp_srt(seconds).replace(",", ".")


def build_srt(items: list[SubtitleItem]) -> str:
    lines: list[str] = []
    for idx, item in enumerate(items, start=1):
        lines.append(str(idx))
        lines.append(f"{format_timestamp_srt(item.start)} --> {format_timestamp_srt(item.end)}")
        lines.append(item.text)
        lines.append("")
    return "\n".join(lines).strip() + "\n"


def build_vtt(items: list[SubtitleItem]) -> str:
    lines = ["WEBVTT", ""]
    for item in items:
        lines.append(f"{format_timestamp_vtt(item.start)} --> {format_timestamp_vtt(item.end)}")
        lines.append(item.text)
        lines.append("")
    return "\n".join(lines).strip() + "\n"


def build_plain_text(items: list[SubtitleItem]) -> str:
    return "\n".join(item.text for item in items) + "\n"


def export_subtitles(
    output_dir: Path,
    subtitles: list[SubtitleItem],
) -> dict[str, Path]:
    subtitles_json = output_dir / "subtitles_mvp.json"
    subtitles_srt = output_dir / "subtitles_mvp.srt"
    subtitles_vtt = output_dir / "subtitles_mvp.vtt"

    json_rows = [{"start": row.start, "end": row.end, "text": row.text} for row in subtitles]
    write_json(subtitles_json, json_rows)
    write_text(subtitles_srt, build_srt(subtitles))
    write_text(subtitles_vtt, build_vtt(subtitles))

    return {
        "subtitles_json": subtitles_json,
        "subtitles_srt": subtitles_srt,
        "subtitles_vtt": subtitles_vtt,
    }


def export_stage4_review_artifacts(
    output_dir: Path,
    subtitles: list[SubtitleItem],
    debug_payload: dict[str, Any],
    noise_subtitles: list[SubtitleItem] | None = None,
) -> dict[str, Path]:
    if noise_subtitles is None:
        noise_subtitles = []

    noise_srt = output_dir / "noise_mvp.srt"
    noise_vtt = output_dir / "noise_mvp.vtt"
    subtitles_debug = output_dir / "subtitles_mvp_debug.json"
    review_text = output_dir / "subtitle_review_text_mvp.txt"

    write_text(noise_srt, build_srt(noise_subtitles))
    write_text(noise_vtt, build_vtt(noise_subtitles))
    write_json(subtitles_debug, debug_payload)
    write_text(review_text, build_plain_text(subtitles))

    return {
        "noise_srt": noise_srt,
        "noise_vtt": noise_vtt,
        "subtitles_debug": subtitles_debug,
        "subtitle_review_text": review_text,
    }
