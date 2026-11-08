from __future__ import annotations

from typing import Any

import cv2


def detect_subtitle_regions(
    frame: Any,
    keep_second_roi: bool = True,
    lower_start_ratio: float = 0.70,
    main_height_ratio: float = 0.22,
    horizontal_margin_ratio: float = 0.10,
) -> list[dict[str, Any]]:
    height, width = frame.shape[:2]

    lower_start = int(height * lower_start_ratio)
    main_y = lower_start
    main_h = max(1, int(height * main_height_ratio))
    main_x = int(width * horizontal_margin_ratio)
    main_w = max(1, int(width * (1.0 - 2 * horizontal_margin_ratio)))

    regions = [
        {
            "name": "main",
            "x": main_x,
            "y": main_y,
            "w": main_w,
            "h": main_h,
            "confidence": 0.9,
        }
    ]

    if keep_second_roi:
        second_h = max(1, int(height * 0.12))
        second_y = max(0, main_y - second_h - int(height * 0.01))
        regions.append(
            {
                "name": "secondary",
                "x": main_x,
                "y": second_y,
                "w": main_w,
                "h": second_h,
                "confidence": 0.75,
            }
        )

    accepted: list[dict[str, Any]] = []
    for region in regions:
        height_ratio = region["h"] / max(1, height)
        too_narrow = region["w"] < int(width * 0.25)
        if int(region["y"]) < lower_start:
            continue
        if height_ratio < 0.10:
            continue
        if too_narrow:
            continue
        accepted.append(region)

    return accepted


def crop_region(frame: Any, region: dict[str, Any]) -> Any:
    x = region["x"]
    y = region["y"]
    w = region["w"]
    h = region["h"]
    return frame[y : y + h, x : x + w]


def save_crop(path: str, crop: Any) -> None:
    cv2.imwrite(path, crop)
