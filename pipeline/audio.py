from __future__ import annotations

import subprocess
from pathlib import Path

from pipeline.io_utils import ensure_dir


def extract_audio_with_ffmpeg(video_path: Path, output_dir: Path, ffmpeg_cmd: str) -> Path:
    ensure_dir(output_dir)
    audio_path = output_dir / "audio_mono_16k.wav"

    command = [
        ffmpeg_cmd,
        "-y",
        "-i",
        str(video_path),
        "-ac",
        "1",
        "-ar",
        "16000",
        str(audio_path),
    ]
    subprocess.run(command, check=True, capture_output=True)
    return audio_path
