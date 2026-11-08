from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import cv2

from models.frame_record import FrameRecord
from pipeline.io_utils import ensure_dir


LOGGER = logging.getLogger(__name__)


def compute_index_padding(sample_count: int) -> int:
    if sample_count <= 0:
        return 1
    return max(1, len(str(max(0, sample_count - 1))))


def build_sampling_plan(total_frames: int, fps: float, interval_seconds: float) -> list[int]:
    if fps <= 0:
        raise ValueError("FPS must be greater than zero")
    if interval_seconds <= 0:
        raise ValueError("Sample interval must be greater than zero")

    step = max(1, int(round(interval_seconds * fps)))
    return list(range(0, total_frames, step))


def resolve_frame_window(total_frames: int, fps: float, start_seconds: float, end_seconds: float | None) -> tuple[int, int]:
    if start_seconds < 0:
        raise ValueError("Start time must be greater than or equal to zero")
    start_frame = int(round(start_seconds * fps))
    start_frame = max(0, min(start_frame, max(0, total_frames - 1)))

    if end_seconds is None:
        end_frame = max(0, total_frames - 1)
    else:
        if end_seconds < start_seconds:
            raise ValueError("End time must be greater than or equal to start time")
        end_frame = int(round(end_seconds * fps))
        end_frame = max(start_frame, min(end_frame, max(0, total_frames - 1)))

    return start_frame, end_frame


def sample_frames(
    video_path: Path,
    sample_interval_seconds: float,
    sampled_frames_dir: Path,
    sampled_frames_rel_dir: str = "sampled_frames",
    start_seconds: float = 0.0,
    end_seconds: float | None = None,
) -> dict[str, Any]:
    ensure_dir(sampled_frames_dir)
    capture = cv2.VideoCapture(str(video_path))
    if not capture.isOpened():
        raise RuntimeError(f"Unable to open video file: {video_path}")

    fps = capture.get(cv2.CAP_PROP_FPS) or 0.0
    total_frames = int(capture.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    start_frame, end_frame = resolve_frame_window(total_frames, fps, start_seconds, end_seconds)

    step = max(1, int(round(sample_interval_seconds * fps)))
    sampling_indices = set(range(start_frame, end_frame + 1, step))
    index_padding = compute_index_padding(len(sampling_indices))
    LOGGER.info(
        "Sampling video '%s' in %.2fs..%.2fs at %.2fs interval (fps=%.3f, total_frames=%s, planned_samples=%s)",
        video_path,
        start_frame / fps,
        end_frame / fps,
        sample_interval_seconds,
        fps,
        total_frames,
        len(sampling_indices),
    )

    records: list[FrameRecord] = []
    frame_number = start_frame
    sample_number = 0

    capture.set(cv2.CAP_PROP_POS_FRAMES, start_frame)

    while True:
        if frame_number > end_frame:
            break

        has_frame, frame = capture.read()
        if not has_frame:
            break

        if frame_number in sampling_indices:
            timestamp = frame_number / fps
            filename = f"frame_{sample_number:0{index_padding}d}.jpg"
            frame_path = sampled_frames_dir / filename
            cv2.imwrite(str(frame_path), frame)
            records.append(
                FrameRecord(
                    index=sample_number,
                    timestamp=round(timestamp, 3),
                    path=f"{sampled_frames_rel_dir}/{filename}",
                )
            )
            sample_number += 1

        frame_number += 1

        if frame_number % 500 == 0 or frame_number == end_frame + 1:
            LOGGER.info(
                "Frame scan progress: %s/%s target frames scanned, %s sampled",
                frame_number,
                end_frame,
                sample_number,
            )

    capture.release()

    return {
        "video": str(video_path),
        "sample_interval_seconds": sample_interval_seconds,
        "start_seconds": round(start_frame / fps, 3),
        "end_seconds": round(end_frame / fps, 3),
        "fps": fps,
        "total_frames": total_frames,
        "index_padding": index_padding,
        "frames": [
            {
                "index": record.index,
                "timestamp": record.timestamp,
                "path": record.path,
            }
            for record in records
        ],
    }
