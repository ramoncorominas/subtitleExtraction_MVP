import numpy as np

from pipeline.roi_detector import detect_subtitle_regions


def test_detect_subtitle_regions_returns_lower_regions() -> None:
    frame = np.zeros((1080, 1920, 3), dtype=np.uint8)
    regions = detect_subtitle_regions(frame, keep_second_roi=True)
    assert regions
    assert all(region["y"] >= int(1080 * 0.7) for region in regions)
