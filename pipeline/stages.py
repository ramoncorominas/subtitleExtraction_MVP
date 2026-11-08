from __future__ import annotations

import shutil
import logging
from pathlib import Path
import time
from typing import Any

import cv2

from app.config import PipelineConfig
from pipeline.audio import extract_audio_with_ffmpeg
from pipeline.dependencies import resolve_runtime_dependencies
from pipeline.demo import export_demo_page
from pipeline.export import export_stage4_review_artifacts, export_subtitles
from pipeline.frame_sampler import sample_frames
from pipeline.io_utils import ensure_dir, write_json
from pipeline.roi_detector import crop_region, detect_subtitle_regions
from pipeline.subtitle_builder import build_segments, consolidate_subtitle_candidates
from pipeline.text_ocr import configure_tesseract, pick_best_ocr_result, preprocess_variants, run_ocr_on_variants


LOGGER = logging.getLogger(__name__)


def _write_stage_artifacts(config: PipelineConfig) -> None:
    LOGGER.info("Creating output directories...")
    for folder in [
        config.output_dir,
        config.debug_dir,
        config.stage_1_dir,
        config.stage_2_dir,
        config.stage_3_dir,
        config.stage_4_dir,
        config.stage_5_dir,
        config.sampled_frames_dir,
        config.frame_crops_dir,
        config.processed_frames_dir,
        config.processed_audio_dir,
    ]:
        ensure_dir(folder)


def stage_preparation(config: PipelineConfig) -> dict[str, Any]:
    LOGGER.info("Stage 1/5 Preparation started")
    started_at = time.perf_counter()
    frame_index = sample_frames(
        video_path=config.video_path,
        sample_interval_seconds=config.sample_interval_seconds,
        sampled_frames_dir=config.sampled_frames_dir,
        sampled_frames_rel_dir=str(config.sampled_frames_dir.relative_to(config.output_dir)).replace("\\", "/"),
        start_seconds=config.start_seconds,
        end_seconds=config.end_seconds,
    )
    LOGGER.info("Sampled %s frames", len(frame_index.get("frames", [])))

    if config.ffmpeg_cmd:
        try:
            LOGGER.info("Extracting audio with ffmpeg: %s", config.ffmpeg_cmd)
            audio_path = extract_audio_with_ffmpeg(
                video_path=config.video_path,
                output_dir=config.processed_audio_dir,
                ffmpeg_cmd=config.ffmpeg_cmd,
            )
            frame_index["processed_audio"] = str(audio_path)
            LOGGER.info("Audio extracted to %s", audio_path)
        except Exception as exc:  # pragma: no cover
            frame_index["processed_audio_error"] = str(exc)
            LOGGER.warning("Audio extraction failed: %s", exc)

    write_json(config.stage_1_dir / "sampled_frames_index.json", frame_index)
    LOGGER.info("Stage 1/5 Preparation finished in %.2fs", time.perf_counter() - started_at)
    return frame_index


def stage_information_retrieval(config: PipelineConfig, frame_index: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    LOGGER.info("Stage 2/5 Information retrieval started")
    started_at = time.perf_counter()
    configure_tesseract(config.tesseract_cmd)
    region_rows: list[dict[str, Any]] = []
    ocr_rows: list[dict[str, Any]] = []

    total_frames = len(frame_index.get("frames", []))
    frame_index_padding = int(frame_index.get("index_padding", max(1, len(str(max(0, total_frames - 1))))))
    LOGGER.info("Running OCR over %s sampled frames", total_frames)

    for idx_frame, frame_record in enumerate(frame_index["frames"], start=1):
        frame_rel = frame_record["path"]
        frame_abs = config.output_dir / frame_rel
        frame = cv2.imread(str(frame_abs))
        if frame is None:
            continue

        timestamp = float(frame_record["timestamp"])
        if config.use_roi_crop:
            regions = detect_subtitle_regions(
                frame,
                keep_second_roi=config.keep_second_roi,
                lower_start_ratio=config.roi_vertical_start_ratio,
                main_height_ratio=config.roi_height_ratio,
                horizontal_margin_ratio=config.roi_horizontal_margin_ratio,
            )
        else:
            height, width = frame.shape[:2]
            regions = [
                {
                    "name": "full_frame",
                    "x": 0,
                    "y": 0,
                    "w": width,
                    "h": height,
                    "confidence": 1.0,
                }
            ]

        for idx, region in enumerate(regions):
            region_rows.append(
                {
                    "frame": frame_rel,
                    "timestamp": timestamp,
                    "region_index": idx,
                    "region": region,
                }
            )

            if config.use_roi_crop:
                crop = crop_region(frame, region)
                crop_filename = f"crop_{frame_record['index']:0{frame_index_padding}d}_{idx}.jpg"
                crop_path = config.frame_crops_dir / crop_filename
                cv2.imwrite(str(crop_path), crop)
                crop_path_value = str(crop_path.relative_to(config.output_dir)).replace("\\", "/")
            else:
                crop = frame
                crop_path_value = frame_rel

            variants = preprocess_variants(crop, use_color_processing=config.use_color_processing)
            variant_results = run_ocr_on_variants(
                variants,
                language=config.ocr_language,
                psm=config.ocr_psm,
            )
            picked = pick_best_ocr_result(variant_results)

            ocr_rows.append(
                {
                    "frame": frame_rel,
                    "timestamp": timestamp,
                    "region_index": idx,
                    "crop_path": crop_path_value,
                    "text_lines": picked.get("text_lines", []),
                    "confidence": picked["confidence"],
                    "best_variant": picked["best_variant"],
                    "all_variants": picked["all_variants"],
                }
            )

        if idx_frame % 20 == 0 or idx_frame == total_frames:
            LOGGER.info(
                "OCR progress: %s/%s frames processed, %s OCR rows",
                idx_frame,
                total_frames,
                len(ocr_rows),
            )

    write_json(config.stage_2_dir / "candidate_regions_mvp.json", region_rows)
    write_json(config.stage_2_dir / "ocr_results_mvp.json", ocr_rows)

    LOGGER.info("Stage 2/5 Information retrieval finished in %.2fs", time.perf_counter() - started_at)
    LOGGER.info("Detected %s regions and %s OCR rows", len(region_rows), len(ocr_rows))

    return region_rows, ocr_rows


def stage_fix_preparation(config: PipelineConfig, ocr_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    LOGGER.info("Stage 3/5 Fix preparation started")
    started_at = time.perf_counter()
    segments = build_segments(
        ocr_results=ocr_rows,
        similarity_threshold=config.merge_similarity_threshold,
        merge_gap_seconds=config.merge_gap_seconds,
        hard_reset_gap_seconds=config.hard_reset_gap_seconds,
        min_text_length=config.min_text_length,
        min_confidence=config.min_ocr_confidence,
    )
    write_json(config.stage_3_dir / "subtitle_segments_mvp.json", segments)
    LOGGER.info("Stage 3/5 Fix preparation finished in %.2fs with %s segments", time.perf_counter() - started_at, len(segments))
    return segments


def stage_generating_fixes(config: PipelineConfig, segments: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    LOGGER.info("Stage 4/5 Generating fixes started")
    started_at = time.perf_counter()
    subtitle_candidates, noise_candidates = consolidate_subtitle_candidates(
        segments=segments,
        min_duration=config.min_subtitle_duration,
        max_duration=config.max_subtitle_duration,
        min_candidate_confidence=config.min_candidate_confidence,
        similarity_threshold=config.merge_similarity_threshold,
        merge_gap_seconds=config.merge_gap_seconds,
    )

    write_json(config.stage_4_dir / "subtitle_candidates_mvp.json", subtitle_candidates)
    write_json(config.stage_4_dir / "noise_candidates_mvp.json", noise_candidates)
    LOGGER.info(
        "Stage 4/5 Generating fixes finished in %.2fs with %s subtitle candidates and %s noise candidates",
        time.perf_counter() - started_at,
        len(subtitle_candidates),
        len(noise_candidates),
    )
    return subtitle_candidates, noise_candidates


def stage_post_production(
    config: PipelineConfig,
    subtitle_candidates: list[dict[str, Any]],
    noise_candidates: list[dict[str, Any]],
) -> dict[str, Any]:
    LOGGER.info("Stage 5/5 Post-production started")
    started_at = time.perf_counter()
    from models.subtitle_item import SubtitleItem

    subtitle_items = [
        SubtitleItem(start=float(row["start"]), end=float(row["end"]), text=str(row["text"]))
        for row in subtitle_candidates
    ]
    noise_items = [
        SubtitleItem(start=float(row["start"]), end=float(row["end"]), text=str(row["text"]))
        for row in noise_candidates
    ]
    debug_payload = {
        "config": {
            "sample_interval_seconds": config.sample_interval_seconds,
            "start_seconds": config.start_seconds,
            "end_seconds": config.end_seconds,
            "ocr_language": config.ocr_language,
            "ocr_psm": config.ocr_psm,
            "use_color_processing": config.use_color_processing,
            "use_roi_crop": config.use_roi_crop,
            "roi_vertical_start_ratio": config.roi_vertical_start_ratio,
            "roi_height_ratio": config.roi_height_ratio,
            "roi_horizontal_margin_ratio": config.roi_horizontal_margin_ratio,
            "min_ocr_confidence": config.min_ocr_confidence,
            "min_candidate_confidence": config.min_candidate_confidence,
            "merge_similarity_threshold": config.merge_similarity_threshold,
        },
        "subtitles_count": len(subtitle_items),
        "noise_count": len(noise_items),
        "subtitles": subtitle_candidates,
        "noise": noise_candidates,
    }

    stage4_artifacts = export_stage4_review_artifacts(
        config.stage_4_dir,
        subtitle_items,
        debug_payload,
        noise_items,
    )

    stage5_video_path = config.stage_5_dir / config.video_path.name
    if config.video_path.resolve() != stage5_video_path.resolve():
        shutil.copy2(config.video_path, stage5_video_path)

    exports = export_subtitles(config.stage_5_dir, subtitle_items)
    demo_subtitles = [
        {"start": row.start, "end": row.end, "text": row.text}
        for row in subtitle_items
    ]
    demo_html = export_demo_page(config.stage_5_dir, stage5_video_path.name, demo_subtitles)

    artifacts = {
        "source_video_copy": str(stage5_video_path),
        "subtitles_json": str(exports["subtitles_json"]),
        "subtitles_srt": str(exports["subtitles_srt"]),
        "subtitles_vtt": str(exports["subtitles_vtt"]),
        "subtitles_demo_html": str(demo_html),
        "stage4_review_artifacts": {
            "noise_srt": str(stage4_artifacts["noise_srt"]),
            "noise_vtt": str(stage4_artifacts["noise_vtt"]),
            "subtitles_debug": str(stage4_artifacts["subtitles_debug"]),
            "subtitle_review_text": str(stage4_artifacts["subtitle_review_text"]),
        },
    }

    write_json(config.stage_5_dir / "pipeline_run_report.json", artifacts)
    LOGGER.info("Stage 5/5 Post-production finished in %.2fs", time.perf_counter() - started_at)
    return artifacts


def run_full_pipeline(config: PipelineConfig) -> dict[str, Any]:
    LOGGER.info("Pipeline run started")
    pipeline_started_at = time.perf_counter()
    _write_stage_artifacts(config)

    deps = resolve_runtime_dependencies(
        app_bin_dir=config.tools_bin_dir,
        allow_bootstrap=config.auto_bootstrap_dependencies,
        forced_tesseract_cmd=config.tesseract_cmd,
        forced_ffmpeg_cmd=config.ffmpeg_cmd,
    )
    LOGGER.info(
        "Dependency resolution: tesseract=%s (%s), ffmpeg=%s (%s)",
        deps["tesseract"].available,
        deps["tesseract"].source,
        deps["ffmpeg"].available,
        deps["ffmpeg"].source,
    )
    if deps["tesseract"].available:
        config.tesseract_cmd = deps["tesseract"].path
    if deps["ffmpeg"].available:
        config.ffmpeg_cmd = deps["ffmpeg"].path

    frame_index = stage_preparation(config)
    _, ocr_rows = stage_information_retrieval(config, frame_index)
    segments = stage_fix_preparation(config, ocr_rows)
    subtitle_candidates, noise_candidates = stage_generating_fixes(config, segments)
    artifacts = stage_post_production(config, subtitle_candidates, noise_candidates)

    result = {
        "dependencies": {
            "tesseract": {
                "available": deps["tesseract"].available,
                "source": deps["tesseract"].source,
                "path": deps["tesseract"].path,
                "note": deps["tesseract"].note,
            },
            "ffmpeg": {
                "available": deps["ffmpeg"].available,
                "source": deps["ffmpeg"].source,
                "path": deps["ffmpeg"].path,
                "note": deps["ffmpeg"].note,
            },
        },
        "sampled_frames": len(frame_index.get("frames", [])),
        "ocr_rows": len(ocr_rows),
        "segments": len(segments),
        "subtitle_candidates": len(subtitle_candidates),
        "noise_candidates": len(noise_candidates),
        "artifacts": artifacts,
    }
    LOGGER.info("Pipeline run finished in %.2fs", time.perf_counter() - pipeline_started_at)
    return result
