from __future__ import annotations

from pathlib import Path
from typing import Any

from app.config import DEFAULT_DEBUG_DIR, DEFAULT_OUTPUT_DIR, PipelineConfig
from pipeline.io_utils import clear_directory
from pipeline.stages import run_full_pipeline


def run_pipeline(
    video_path: Path,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    debug_dir: Path = DEFAULT_DEBUG_DIR,
    sample_interval_seconds: float = 0.5,
    start_seconds: float = 0.0,
    end_seconds: float | None = None,
    ocr_language: str = "eng",
    ocr_psm: int = 6,
    use_color_processing: bool = True,
    use_roi_crop: bool = True,
    roi_vertical_start_ratio: float = 0.7,
    roi_height_ratio: float = 0.22,
    roi_horizontal_margin_ratio: float = 0.10,
    keep_second_roi: bool = True,
    min_ocr_confidence: float = 65.0,
    min_candidate_confidence: float = 0.0,
    tesseract_cmd: str | None = None,
    ffmpeg_cmd: str | None = None,
    auto_bootstrap_dependencies: bool = True,
    clean_output: bool = False,
) -> dict[str, Any]:
    if clean_output:
        clear_directory(output_dir)
        clear_directory(debug_dir)

    config = PipelineConfig(
        video_path=video_path,
        output_dir=output_dir,
        debug_dir=debug_dir,
        sample_interval_seconds=sample_interval_seconds,
        start_seconds=start_seconds,
        end_seconds=end_seconds,
        ocr_language=ocr_language,
        ocr_psm=ocr_psm,
        use_color_processing=use_color_processing,
        use_roi_crop=use_roi_crop,
        roi_vertical_start_ratio=roi_vertical_start_ratio,
        roi_height_ratio=roi_height_ratio,
        roi_horizontal_margin_ratio=roi_horizontal_margin_ratio,
        keep_second_roi=keep_second_roi,
        min_ocr_confidence=min_ocr_confidence,
        min_candidate_confidence=min_candidate_confidence,
        tesseract_cmd=tesseract_cmd,
        ffmpeg_cmd=ffmpeg_cmd,
        auto_bootstrap_dependencies=auto_bootstrap_dependencies,
    )
    return run_full_pipeline(config)
