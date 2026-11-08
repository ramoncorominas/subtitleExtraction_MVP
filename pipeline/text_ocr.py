from __future__ import annotations

import re
from typing import Any

import cv2
import numpy as np
import pytesseract


def configure_tesseract(tesseract_cmd: str | None) -> None:
    if tesseract_cmd:
        pytesseract.pytesseract.tesseract_cmd = tesseract_cmd


def preprocess_variants(crop: Any, use_color_processing: bool = True) -> dict[str, Any]:
    if not use_color_processing:
        return {"original": crop}

    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)

    contrast = cv2.convertScaleAbs(gray, alpha=1.7, beta=0)
    sharpen_kernel = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]])
    sharpened = cv2.filter2D(gray, ddepth=-1, kernel=sharpen_kernel)
    _, thresholded = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    return {
        "original": crop,
        "grayscale": gray,
        "contrast": contrast,
        "thresholded": thresholded,
        "sharpened": sharpened,
    }


def clean_ocr_text(text: str) -> str:
    text = text.strip()
    text = re.sub(r"\s+", " ", text)
    text = text.replace("|", "I")
    return text


def _extract_text_confidence(ocr_data: dict[str, list[Any]]) -> tuple[str, float, list[dict[str, Any]]]:
    tokens: list[str] = []
    conf_values: list[float] = []
    grouped_lines: dict[tuple[str, str, str], dict[str, Any]] = {}
    ordered_keys: list[tuple[str, str, str]] = []

    texts = ocr_data.get("text", [])
    confs = ocr_data.get("conf", [])
    blocks = ocr_data.get("block_num", [])
    paragraphs = ocr_data.get("par_num", [])
    lines = ocr_data.get("line_num", [])

    for idx, token in enumerate(texts):
        value = token.strip()
        if not value:
            continue

        conf_raw = confs[idx] if idx < len(confs) else "-1"
        try:
            conf = float(conf_raw)
        except (TypeError, ValueError):
            conf = -1.0
        if conf < 0:
            continue

        tokens.append(value)
        conf_values.append(conf)

        block = str(blocks[idx]) if idx < len(blocks) else "0"
        paragraph = str(paragraphs[idx]) if idx < len(paragraphs) else "0"
        line = str(lines[idx]) if idx < len(lines) else str(idx)
        key = (block, paragraph, line)

        if key not in grouped_lines:
            grouped_lines[key] = {"tokens": [], "conf_values": []}
            ordered_keys.append(key)

        grouped_lines[key]["tokens"].append(value)
        grouped_lines[key]["conf_values"].append(conf)

    if not tokens:
        return "", 0.0, []

    text = clean_ocr_text(" ".join(tokens))
    confidence = sum(conf_values) / len(conf_values)

    line_payload: list[dict[str, Any]] = []
    for key in ordered_keys:
        line_tokens = grouped_lines[key]["tokens"]
        line_conf_values = grouped_lines[key]["conf_values"]
        line_text = clean_ocr_text(" ".join(line_tokens))
        if not line_text:
            continue
        line_confidence = sum(line_conf_values) / len(line_conf_values) if line_conf_values else 0.0
        line_payload.append(
            {
                "text": line_text,
                "confidence": round(line_confidence, 2),
            }
        )

    return text, confidence, line_payload


def _has_useful_line(text_lines: list[dict[str, Any]]) -> bool:
    for item in text_lines:
        if not isinstance(item, dict):
            continue
        if str(item.get("text", "")).strip():
            return True
    return False


def _line_driven_confidence(text_lines: list[dict[str, Any]]) -> float:
    confidences = [float(item.get("confidence", 0.0)) for item in text_lines if isinstance(item, dict)]
    if not confidences:
        return 0.0
    confidences.sort(reverse=True)
    top_confidences = confidences[:2]
    return round(sum(top_confidences) / len(top_confidences), 2)


def run_ocr_on_variants(
    variants: dict[str, Any],
    language: str = "eng",
    psm: int = 6,
) -> dict[str, dict[str, Any]]:
    results: dict[str, dict[str, Any]] = {}
    config = f"--oem 3 --psm {psm}"

    for name, image in variants.items():
        data = pytesseract.image_to_data(
            image,
            output_type=pytesseract.Output.DICT,
            config=config,
            lang=language,
        )
        _, _, text_lines = _extract_text_confidence(data)
        results[name] = {
            "confidence": _line_driven_confidence(text_lines),
            "text_lines": text_lines,
        }

    return results


def pick_best_ocr_result(variant_results: dict[str, dict[str, Any]]) -> dict[str, Any]:
    best_name = ""
    best_conf = 0.0
    best_text_lines: list[dict[str, Any]] = []

    for variant_name, payload in variant_results.items():
        conf = payload["confidence"]
        text_lines = payload.get("text_lines", [])
        if not _has_useful_line(text_lines):
            continue
        if conf > best_conf:
            best_name = variant_name
            best_conf = conf
            best_text_lines = text_lines

    return {
        "best_variant": best_name,
        "confidence": best_conf,
        "text_lines": best_text_lines,
        "all_variants": variant_results,
    }
