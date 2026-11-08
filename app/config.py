from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass(slots=True)
class PipelineConfig:
    video_path: Path
    output_dir: Path
    debug_dir: Path
    sample_interval_seconds: float = 0.5
    start_seconds: float = 0.0
    end_seconds: float | None = None
    ocr_language: str = "eng"
    ocr_psm: int = 6
    use_color_processing: bool = True
    use_roi_crop: bool = True
    roi_vertical_start_ratio: float = 0.7
    roi_height_ratio: float = 0.22
    roi_horizontal_margin_ratio: float = 0.10
    min_ocr_confidence: float = 65.0
    accept_variant_confidence: float = 70.0
    merge_similarity_threshold: float = 0.88
    merge_gap_seconds: float = 2.5
    hard_reset_gap_seconds: float = 10.0
    min_subtitle_duration: float = 0.8
    max_subtitle_duration: float = 10.0
    min_text_length: int = 2
    min_candidate_confidence: float = 0.0
    tesseract_cmd: Optional[str] = None
    ffmpeg_cmd: Optional[str] = None
    keep_second_roi: bool = True
    auto_bootstrap_dependencies: bool = True
    stage_1_dir: Path = field(init=False)
    stage_2_dir: Path = field(init=False)
    stage_3_dir: Path = field(init=False)
    stage_4_dir: Path = field(init=False)
    stage_5_dir: Path = field(init=False)
    sampled_frames_dir: Path = field(init=False)
    frame_crops_dir: Path = field(init=False)
    processed_frames_dir: Path = field(init=False)
    processed_audio_dir: Path = field(init=False)
    project_root: Path = field(init=False)
    tools_bin_dir: Path = field(init=False)

    def __post_init__(self) -> None:
        self.stage_1_dir = self.output_dir / "stage-1-preparation"
        self.stage_2_dir = self.output_dir / "stage-2-info-retrieval"
        self.stage_3_dir = self.output_dir / "stage-3-fix-preparation"
        self.stage_4_dir = self.output_dir / "stage-4-generating-fixes"
        self.stage_5_dir = self.output_dir / "stage-5-post-production"
        self.sampled_frames_dir = self.stage_1_dir / "sampled_frames"
        self.frame_crops_dir = self.stage_2_dir / "frame_crops"
        self.processed_frames_dir = self.stage_2_dir / "processed_frames"
        self.processed_audio_dir = self.stage_1_dir / "processed_audio"
        self.project_root = Path(__file__).resolve().parent.parent
        self.tools_bin_dir = self.project_root / "tools" / "bin"


DEFAULT_DATA_DIR = Path("data")
DEFAULT_INPUT_DIR = DEFAULT_DATA_DIR / "input"
DEFAULT_OUTPUT_DIR = DEFAULT_DATA_DIR / "output"
DEFAULT_DEBUG_DIR = DEFAULT_DATA_DIR / "debug"
