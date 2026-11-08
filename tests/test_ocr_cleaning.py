from pipeline.subtitle_builder import build_segments, normalize_text


def test_normalize_text_compacts_spaces() -> None:
    text = "  HELLO   world!!  "
    assert normalize_text(text) == "hello world!!"


def test_build_segments_filters_multiline_noise_and_keeps_main_line() -> None:
    ocr_results = [
        {
            "timestamp": 1.0,
            "frame": "sampled_frames/frame_000049.jpg",
            "confidence": 90.0,
            "text": "rtve ... MUCHACHITO BOMBO INFIERNO - Siempre que quiera",
            "text_lines": [
                {"text": "rtve", "confidence": 99.0},
                {"text": "y 7 p 5", "confidence": 86.0},
                {"text": "MUCHACHITO BOMBO INFIERNO - Siempre que quiera", "confidence": 92.0},
                {"text": "(Musica Uno, 2005)", "confidence": 90.0},
            ],
        }
    ]

    segments = build_segments(
        ocr_results=ocr_results,
        similarity_threshold=0.88,
        merge_gap_seconds=2.5,
        hard_reset_gap_seconds=10.0,
        min_text_length=2,
        min_confidence=65.0,
    )

    assert len(segments) == 1
    assert segments[0]["text"] == "MUCHACHITO BOMBO INFIERNO - Siempre que quiera\n(Musica Uno, 2005)"
    assert "rtve" not in segments[0]["normalized_text"]


def test_build_segments_drops_row_when_all_detected_lines_are_noise() -> None:
    ocr_results = [
        {
            "timestamp": 1.0,
            "frame": "sampled_frames/frame_000010.jpg",
            "confidence": 90.0,
            "text": "rtve y 7 p 5",
            "text_lines": [
                {"text": "rtve", "confidence": 99.0},
                {"text": "y 7 p 5", "confidence": 80.0},
            ],
        }
    ]

    segments = build_segments(
        ocr_results=ocr_results,
        similarity_threshold=0.88,
        merge_gap_seconds=2.5,
        hard_reset_gap_seconds=10.0,
        min_text_length=2,
        min_confidence=65.0,
    )

    assert segments == []


def test_build_segments_uses_line_confidence_threshold() -> None:
    ocr_results = [
        {
            "timestamp": 1.0,
            "frame": "sampled_frames/frame_000010.jpg",
            "confidence": 40.0,
            "text_lines": [
                {"text": "rtve y 7 p 5", "confidence": 55.0},
                {"text": "Muchachito vive en las antipodas", "confidence": 91.0},
            ],
        }
    ]

    segments = build_segments(
        ocr_results=ocr_results,
        similarity_threshold=0.88,
        merge_gap_seconds=2.5,
        hard_reset_gap_seconds=10.0,
        min_text_length=2,
        min_confidence=65.0,
    )

    assert len(segments) == 1
    assert segments[0]["text"] == "Muchachito vive en las antipodas"


def test_build_segments_merges_near_duplicate_consecutive_frames() -> None:
    ocr_results = [
        {
            "timestamp": 1.00,
            "frame": "sampled_frames/frame_000001.jpg",
            "confidence": 90.0,
            "text_lines": [{"text": "Siempre que quiera", "confidence": 90.0}],
        },
        {
            "timestamp": 1.25,
            "frame": "sampled_frames/frame_000002.jpg",
            "confidence": 87.0,
            "text_lines": [{"text": "Siempre que quera", "confidence": 87.0}],
        },
        {
            "timestamp": 1.50,
            "frame": "sampled_frames/frame_000003.jpg",
            "confidence": 92.0,
            "text_lines": [{"text": "Siempre que quiera", "confidence": 92.0}],
        },
    ]

    segments = build_segments(
        ocr_results=ocr_results,
        similarity_threshold=0.88,
        merge_gap_seconds=2.5,
        hard_reset_gap_seconds=10.0,
        min_text_length=2,
        min_confidence=65.0,
    )

    assert len(segments) == 1
    assert segments[0]["text"] == "Siempre que quiera"
    assert segments[0]["event_count"] == 3


def test_build_segments_consensus_picks_most_repeated_variant() -> None:
    ocr_results = [
        {
            "timestamp": 1.00,
            "frame": "sampled_frames/frame_000010.jpg",
            "confidence": 88.0,
            "text_lines": [{"text": "MUCHACHITO BOMBO INFIERNO", "confidence": 88.0}],
        },
        {
            "timestamp": 1.25,
            "frame": "sampled_frames/frame_000011.jpg",
            "confidence": 86.0,
            "text_lines": [{"text": "MUCHACHITO BOMBO INFERNO", "confidence": 86.0}],
        },
        {
            "timestamp": 1.50,
            "frame": "sampled_frames/frame_000012.jpg",
            "confidence": 87.0,
            "text_lines": [{"text": "MUCHACHITO BOMBO INFIERNO", "confidence": 87.0}],
        },
    ]

    segments = build_segments(
        ocr_results=ocr_results,
        similarity_threshold=0.88,
        merge_gap_seconds=2.5,
        hard_reset_gap_seconds=10.0,
        min_text_length=2,
        min_confidence=65.0,
    )

    assert len(segments) == 1
    assert segments[0]["text"] == "MUCHACHITO BOMBO INFIERNO"
