from dataclasses import dataclass


@dataclass(slots=True)
class FrameRecord:
    index: int
    timestamp: float
    path: str
