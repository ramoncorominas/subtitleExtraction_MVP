from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from pathlib import Path

from app.config import DEFAULT_DEBUG_DIR, DEFAULT_OUTPUT_DIR
from app.main import run_pipeline


def build_default_output_dirs(
    output_dir: str | Path | None = None,
    debug_dir: str | Path | None = None,
) -> tuple[Path, Path]:
    resolved_output_dir = Path(output_dir) if output_dir is not None else DEFAULT_OUTPUT_DIR
    resolved_debug_dir = Path(debug_dir) if debug_dir is not None else DEFAULT_DEBUG_DIR
    return resolved_output_dir, resolved_debug_dir


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Subtitle extraction MVP pipeline")
    parser.add_argument("--video", required=True, type=Path, help="Path to input video")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Directory for generated output files (defaults to data/output)",
    )
    parser.add_argument(
        "--debug-dir",
        type=Path,
        default=None,
        help="Directory for debug files (defaults to data/debug)",
    )
    parser.add_argument(
        "--sample-interval",
        type=float,
        default=0.5,
        help="Frame sample interval in seconds",
    )
    parser.add_argument(
        "--start",
        type=float,
        default=0.0,
        help="Start time in seconds for frame sampling",
    )
    parser.add_argument(
        "--end",
        type=float,
        default=None,
        help="End time in seconds for frame sampling (optional)",
    )
    parser.add_argument(
        "--lang",
        type=str,
        default="eng",
        help="OCR language code for Tesseract (for example: eng, spa)",
    )
    parser.add_argument(
        "--ocr-psm",
        type=int,
        default=6,
        help="Tesseract page segmentation mode (PSM)",
    )
    parser.add_argument(
        "--min-ocr-confidence",
        type=float,
        default=65.0,
        help="Minimum OCR confidence",
    )
    parser.add_argument(
        "--min-candidate-confidence",
        type=float,
        default=0.0,
        help="Minimum confidence for subtitle candidates after OCR merging",
    )
    parser.add_argument(
        "--no-color-processing",
        action="store_true",
        help="Disable extra OCR color/preprocessing variants; use original crop only",
    )
    parser.add_argument(
        "--disable-roi-crop",
        action="store_true",
        help="Disable ROI cropping and run OCR on full sampled frames",
    )
    parser.add_argument(
        "--no-secondary-roi",
        action="store_true",
        help="Disable secondary ROI candidate",
    )
    parser.add_argument(
        "--roi-y-start",
        type=float,
        default=0.7,
        help="ROI start position as ratio of frame height",
    )
    parser.add_argument(
        "--roi-height-ratio",
        type=float,
        default=0.22,
        help="Main ROI height as ratio of frame height",
    )
    parser.add_argument(
        "--roi-x-margin-ratio",
        type=float,
        default=0.10,
        help="Horizontal ROI margin ratio on each side",
    )
    parser.add_argument(
        "--tesseract-cmd",
        type=str,
        default=None,
        help="Optional custom tesseract executable path",
    )
    parser.add_argument(
        "--ffmpeg-cmd",
        type=str,
        default=None,
        help="Optional custom ffmpeg executable path",
    )
    parser.add_argument(
        "--no-auto-bootstrap",
        action="store_true",
        help="Disable dependency auto-bootstrap (system/app/download checks)",
    )
    parser.add_argument(
        "--clean-output",
        "--clear-output",
        action="store_true",
        help="Delete all existing files in the output and debug folders before starting the run",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )
    return parser


def configure_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%H:%M:%S",
    )


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    if args.output_dir is None or args.debug_dir is None:
        args.output_dir, args.debug_dir = build_default_output_dirs(args.output_dir, args.debug_dir)
    configure_logging(args.verbose)

    print("[subtitle-mvp] Starting pipeline run...", flush=True)
    print(f"[subtitle-mvp] Video: {args.video}", flush=True)
    started_at = time.perf_counter()

    try:
        if args.clean_output:
            print(f"[subtitle-mvp] Cleaning output folder: {args.output_dir}", flush=True)
            print(f"[subtitle-mvp] Cleaning debug folder: {args.debug_dir}", flush=True)
            from pipeline.io_utils import clear_directory

            clear_directory(args.output_dir)
            clear_directory(args.debug_dir)

        result = run_pipeline(
            video_path=args.video,
            output_dir=args.output_dir,
            debug_dir=args.debug_dir,
            sample_interval_seconds=args.sample_interval,
            start_seconds=args.start,
            end_seconds=args.end,
            ocr_language=args.lang,
            ocr_psm=args.ocr_psm,
            use_color_processing=not args.no_color_processing,
            use_roi_crop=not args.disable_roi_crop,
            roi_vertical_start_ratio=args.roi_y_start,
            roi_height_ratio=args.roi_height_ratio,
            roi_horizontal_margin_ratio=args.roi_x_margin_ratio,
            keep_second_roi=not args.no_secondary_roi,
            min_ocr_confidence=args.min_ocr_confidence,
            min_candidate_confidence=args.min_candidate_confidence,
            tesseract_cmd=args.tesseract_cmd,
            ffmpeg_cmd=args.ffmpeg_cmd,
            auto_bootstrap_dependencies=not args.no_auto_bootstrap,
            clean_output=args.clean_output,
        )
    except Exception as exc:
        print(f"[subtitle-mvp] Pipeline failed: {exc}", file=sys.stderr, flush=True)
        logging.getLogger(__name__).exception("Pipeline run failed")
        raise

    elapsed = time.perf_counter() - started_at
    print(f"[subtitle-mvp] Pipeline finished in {elapsed:.2f}s", flush=True)

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
