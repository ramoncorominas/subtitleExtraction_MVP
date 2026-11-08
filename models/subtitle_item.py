from dataclasses import dataclass


@dataclass(slots=True)
class SubtitleItem:
    start: float
    end: float
    text: str
