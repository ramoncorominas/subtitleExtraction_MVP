from pipeline.subtitle_builder import consolidate_subtitle_candidates


def test_consolidation_removes_repeated_watermark_and_collects_noise() -> None:
    segments = [
        {
            "start": 1.0,
            "end": 1.4,
            "text": "rtve Hola mundo",
            "avg_confidence": 80.0,
        },
        {
            "start": 1.4,
            "end": 2.0,
            "text": "rtve Hola mundo",
            "avg_confidence": 82.0,
        },
        {
            "start": 2.0,
            "end": 2.4,
            "text": "rtve Hola mundo #musica",
            "avg_confidence": 79.0,
        },
    ]

    subtitles, noise = consolidate_subtitle_candidates(
        segments=segments,
        min_duration=0.8,
        max_duration=10.0,
        min_candidate_confidence=0.0,
        similarity_threshold=0.88,
        merge_gap_seconds=2.5,
    )

    assert len(subtitles) == 1
    assert subtitles[0]["text"].lower() == "hola mundo"
    assert len(noise) >= 1
    assert "rtve" in noise[0]["text"].lower() or "#musica" in noise[0]["text"].lower()


def test_consolidation_respects_candidate_confidence_threshold() -> None:
    segments = [
        {"start": 0.0, "end": 0.2, "text": "Hola", "avg_confidence": 55.0},
        {"start": 1.0, "end": 1.2, "text": "Adios", "avg_confidence": 85.0},
    ]

    subtitles, _ = consolidate_subtitle_candidates(
        segments=segments,
        min_duration=0.8,
        max_duration=10.0,
        min_candidate_confidence=70.0,
        similarity_threshold=0.88,
        merge_gap_seconds=2.5,
    )

    assert len(subtitles) == 1
    assert subtitles[0]["text"] == "Adios"


def test_consolidation_drops_weak_short_artifact_to_noise() -> None:
    segments = [
        {
            "start": 10.0,
            "end": 10.2,
            "text": "KT,",
            "avg_confidence": 67.0,
            "event_count": 1,
        }
    ]

    subtitles, noise = consolidate_subtitle_candidates(
        segments=segments,
        min_duration=0.8,
        max_duration=10.0,
        min_candidate_confidence=0.0,
        similarity_threshold=0.88,
        merge_gap_seconds=2.5,
    )

    assert subtitles == []
    assert len(noise) == 1
    assert noise[0]["source"] == "short_artifact"


def test_consolidation_keeps_obvious_short_subtitle_when_repeated() -> None:
    segments = [
        {
            "start": 5.0,
            "end": 5.2,
            "text": "No.",
            "avg_confidence": 93.0,
            "event_count": 4,
        }
    ]

    subtitles, noise = consolidate_subtitle_candidates(
        segments=segments,
        min_duration=0.8,
        max_duration=10.0,
        min_candidate_confidence=0.0,
        similarity_threshold=0.88,
        merge_gap_seconds=2.5,
    )

    assert len(subtitles) == 1
    assert subtitles[0]["text"] == "No."
    assert noise == []


def test_consolidation_strips_ocr_edge_symbols_from_text() -> None:
    segments = [
        {
            "start": 1.0,
            "end": 2.0,
            "text": "£ Hola mundo «>",
            "avg_confidence": 90.0,
            "event_count": 3,
        }
    ]

    subtitles, _ = consolidate_subtitle_candidates(
        segments=segments,
        min_duration=0.8,
        max_duration=10.0,
        min_candidate_confidence=0.0,
        similarity_threshold=0.88,
        merge_gap_seconds=2.5,
    )

    assert len(subtitles) == 1
    assert subtitles[0]["text"] == "Hola mundo"