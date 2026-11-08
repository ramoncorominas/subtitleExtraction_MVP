from models.subtitle_item import SubtitleItem
from pipeline.export import build_srt, build_vtt


def test_build_srt_contains_timestamp() -> None:
    text = build_srt([SubtitleItem(start=0.0, end=1.25, text="Hello")])
    assert "00:00:00,000 --> 00:00:01,250" in text


def test_build_vtt_has_header() -> None:
    text = build_vtt([SubtitleItem(start=0.0, end=1.25, text="Hello")])
    assert text.startswith("WEBVTT")
