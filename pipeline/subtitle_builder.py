from __future__ import annotations

import re
from dataclasses import asdict
from difflib import SequenceMatcher
from typing import Any

from models.subtitle_item import SubtitleItem

try:
    from rapidfuzz import fuzz
except ImportError:  # pragma: no cover
    fuzz = None


KNOWN_WATERMARK_TOKENS = {
    "rtve",
    "la1",
    "la2",
    "telecinco",
    "antena3",
    "atresplayer",
    "netflix",
    "hbo",
    "primevideo",
    "disney",
}

OBVIOUS_SHORT_SUBTITLE_TOKENS = {
    "si",
    "no",
    "ok",
    "eh",
    "ay",
    "oh",
    "uy",
    "vale",
    "bien",
}


def normalize_text(text: str) -> str:
    text = text.strip().lower()
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"[^\w\s'\-.,?!]", "", text)
    return text


def is_mostly_symbols(text: str) -> bool:
    filtered = re.sub(r"\s", "", text)
    if not filtered:
        return True
    symbol_count = len(re.findall(r"[^\w]", filtered))
    return symbol_count / len(filtered) > 0.7


def text_similarity(left: str, right: str) -> float:
    if not left or not right:
        return 0.0
    if fuzz is not None:
        return fuzz.ratio(left, right) / 100.0
    return SequenceMatcher(None, left, right).ratio()


def _compact_spaces(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _compact_spaces_keep_lines(text: str) -> str:
    cleaned_lines = [_compact_spaces(line) for line in text.splitlines()]
    cleaned_lines = [line for line in cleaned_lines if line]
    return "\n".join(cleaned_lines)


def _strip_ocr_edge_symbols(text: str) -> str:
    cleaned_lines: list[str] = []
    for raw_line in text.splitlines():
        line = _compact_spaces(raw_line)
        if not line:
            continue
        line = re.sub(r"^[^\w\(\[\{\"'¿¡]+", "", line)
        line = re.sub(r"[^\w\)\]\}\"'.,?!¿¡]+$", "", line)
        line = _compact_spaces(line)
        if line:
            cleaned_lines.append(line)
    return "\n".join(cleaned_lines)


def _clean_consensus_text(text: str) -> str:
    cleaned = _strip_ocr_edge_symbols(text)
    return _compact_spaces_keep_lines(cleaned)


def _normalize_token(token: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", token.lower())


def _line_looks_like_watermark_noise(normalized_line: str) -> bool:
    tokens = [tok for tok in normalized_line.split(" ") if tok]
    if not tokens:
        return True

    normalized_tokens = [_normalize_token(tok) for tok in tokens]
    meaningful = [tok for tok in normalized_tokens if len(tok) >= 3]

    if not meaningful and len(normalized_tokens) >= 2:
        return True

    first_token = next((tok for tok in normalized_tokens if tok), "")
    if first_token in KNOWN_WATERMARK_TOKENS:
        non_watermark_meaningful = [tok for tok in meaningful if tok not in KNOWN_WATERMARK_TOKENS]
        if not non_watermark_meaningful:
            return True

    return False


def _trim_leading_noise_tokens(text: str) -> str:
    tokens = [tok for tok in _compact_spaces(text).split(" ") if tok]
    if not tokens:
        return ""

    if _normalize_token(tokens[0]) not in KNOWN_WATERMARK_TOKENS:
        return " ".join(tokens)

    idx = 0
    while idx < len(tokens):
        token = tokens[idx]
        normalized = _normalize_token(token)
        if not normalized or normalized in KNOWN_WATERMARK_TOKENS or len(normalized) <= 2:
            idx += 1
            continue
        break

    if idx >= len(tokens):
        return ""
    return " ".join(tokens[idx:])


def _build_text_from_detected_lines(
    row: dict[str, Any],
    min_text_length: int,
    min_line_confidence: float,
) -> tuple[str, float | None]:
    raw_lines = row.get("text_lines", [])
    if not isinstance(raw_lines, list) or not raw_lines:
        fallback_text = str(row.get("text", "")).strip()
        fallback_confidence = float(row.get("confidence", 0.0)) if fallback_text else None
        return fallback_text, fallback_confidence

    accepted_lines: list[dict[str, Any]] = []
    for line in raw_lines:
        if isinstance(line, dict):
            line_text = str(line.get("text", "")).strip()
            line_confidence = float(line.get("confidence", row.get("confidence", 0.0)))
        else:
            line_text = str(line).strip()
            line_confidence = float(row.get("confidence", 0.0))

        if not line_text:
            continue
        if line_confidence < min_line_confidence:
            continue

        line_text = _trim_leading_noise_tokens(line_text)
        if not line_text:
            continue

        normalized_line = normalize_text(line_text)
        if len(normalized_line) < min_text_length:
            continue
        if is_mostly_symbols(normalized_line):
            continue
        if _line_looks_like_watermark_noise(normalized_line):
            continue

        accepted_lines.append(
            {
                "text": line_text,
                "confidence": line_confidence,
            }
        )

    if not accepted_lines:
        return "", None

    best_confidence = max(float(item["confidence"]) for item in accepted_lines)
    threshold = max(min_line_confidence, best_confidence - 10.0)
    selected_lines = [item["text"] for item in accepted_lines if float(item["confidence"]) >= threshold]
    selected_confidences = [float(item["confidence"]) for item in accepted_lines if float(item["confidence"]) >= threshold]
    if not selected_lines:
        return "", None

    selected_confidences.sort(reverse=True)
    top_confidences = selected_confidences[:2]
    line_driven_confidence = sum(top_confidences) / len(top_confidences)

    return "\n".join(selected_lines), round(line_driven_confidence, 2)


def detect_repeated_prefix_noise(texts: list[str], min_occurrences: int = 3) -> list[str]:
    prefix_counts: dict[str, int] = {}

    for text in texts:
        tokens = [t for t in _compact_spaces(text).split(" ") if t]
        if not tokens:
            continue

        max_len = 1
        for size in range(1, max_len + 1):
            phrase = " ".join(tokens[:size])
            normalized_tokens = [_normalize_token(tok) for tok in phrase.split(" ")]
            if not any(normalized_tokens):
                continue

            has_known_token = any(token in KNOWN_WATERMARK_TOKENS for token in normalized_tokens if token)
            mostly_short_tokens = all(len(token) <= 12 for token in normalized_tokens if token)

            if has_known_token or (size == 1 and mostly_short_tokens):
                key = _compact_spaces(phrase.lower())
                prefix_counts[key] = prefix_counts.get(key, 0) + 1

    return sorted([k for k, count in prefix_counts.items() if count >= min_occurrences], key=len, reverse=True)


def extract_noise_fragments(text: str, repeated_prefix_noise: list[str]) -> tuple[str, list[str]]:
    noise_fragments: list[str] = []
    cleaned = _compact_spaces_keep_lines(text)
    if not cleaned:
        return "", noise_fragments

    cleaned_lines: list[str] = []
    for raw_line in cleaned.splitlines():
        line = _compact_spaces(raw_line)
        if not line:
            continue

        hashtag_matches = re.findall(r"#\w+", line, flags=re.IGNORECASE)
        if hashtag_matches:
            noise_fragments.extend(hashtag_matches)
            line = _compact_spaces(re.sub(r"#\w+", " ", line, flags=re.IGNORECASE))
            if not line:
                continue

        changed = True
        while changed and line:
            changed = False
            lowered = line.lower()
            for prefix in repeated_prefix_noise:
                if lowered.startswith(prefix):
                    original_prefix = line[: len(prefix)]
                    noise_fragments.append(_compact_spaces(original_prefix))
                    line = _compact_spaces(line[len(prefix) :])
                    changed = True
                    break

        if line:
            cleaned_lines.append(line)

    cleaned = "\n".join(cleaned_lines)
    return cleaned, [fragment for fragment in noise_fragments if fragment]


def _ensure_non_overlapping(items: list[dict[str, Any]], min_duration: float) -> list[dict[str, Any]]:
    if not items:
        return []

    resolved: list[dict[str, Any]] = []
    for item in sorted(items, key=lambda row: (float(row["start"]), float(row["end"]))):
        row = dict(item)
        start = float(row["start"])
        end = float(row["end"])

        if resolved:
            prev = resolved[-1]
            prev_end = float(prev["end"])
            if start < prev_end:
                start = prev_end

        if end <= start:
            end = start + min_duration

        row["start"] = round(start, 3)
        row["end"] = round(end, 3)
        resolved.append(row)

    return resolved


def _candidate_similarity_score(left: str, right: str) -> float:
    similarity = text_similarity(left, right)
    if similarity >= 0.88:
        return similarity

    left_tokens = [token for token in left.split(" ") if token]
    right_tokens = [token for token in right.split(" ") if token]
    if not left_tokens or not right_tokens:
        return similarity

    left_set = set(left_tokens)
    right_set = set(right_tokens)
    overlap = len(left_set & right_set)
    token_jaccard = overlap / max(len(left_set | right_set), 1)

    if left in right or right in left:
        return max(similarity, 0.9)
    if token_jaccard >= 0.8:
        return max(similarity, token_jaccard)

    return similarity


def _event_fits_segment(event: dict[str, Any], segment_events: list[dict[str, Any]], similarity_threshold: float) -> bool:
    event_normalized = str(event.get("normalized_text", ""))
    if not event_normalized:
        return False

    # Compare against the full cluster so minor OCR drifts do not break continuity.
    best_similarity = 0.0
    for member in segment_events:
        member_normalized = str(member.get("normalized_text", ""))
        if not member_normalized:
            continue
        best_similarity = max(best_similarity, _candidate_similarity_score(event_normalized, member_normalized))
        if best_similarity >= similarity_threshold:
            return True

    relaxed_threshold = max(0.75, similarity_threshold - 0.08)
    return best_similarity >= relaxed_threshold


def _pick_consensus_event(events: list[dict[str, Any]]) -> dict[str, Any]:
    if not events:
        return {"text": "", "normalized_text": ""}

    best_event = events[0]
    best_score = -1.0

    for candidate in events:
        candidate_normalized = str(candidate.get("normalized_text", ""))
        if not candidate_normalized:
            continue

        score = 0.0
        for other in events:
            other_normalized = str(other.get("normalized_text", ""))
            if not other_normalized:
                continue
            confidence_weight = max(float(other.get("confidence", 0.0)), 1.0)
            score += _candidate_similarity_score(candidate_normalized, other_normalized) * confidence_weight

        candidate_confidence = float(candidate.get("confidence", 0.0))
        best_confidence = float(best_event.get("confidence", 0.0))
        if (
            score > best_score
            or (score == best_score and candidate_confidence > best_confidence)
            or (
                score == best_score
                and candidate_confidence == best_confidence
                and len(str(candidate.get("text", ""))) > len(str(best_event.get("text", "")))
            )
        ):
            best_score = score
            best_event = candidate

    cleaned_text = _clean_consensus_text(str(best_event.get("text", "")))
    normalized = normalize_text(cleaned_text)
    return {
        "text": cleaned_text,
        "normalized_text": normalized,
    }


def _is_obvious_short_subtitle(text: str, normalized_text: str, confidence: float, evidence_count: int) -> bool:
    tokens = [token for token in normalized_text.split(" ") if token]
    if not tokens:
        return False

    if len(tokens) == 1:
        token = re.sub(r"[^a-z0-9]+", "", tokens[0].lower())
        if token in OBVIOUS_SHORT_SUBTITLE_TOKENS:
            return True
        if len(token) >= 5 and confidence >= 80.0:
            return True
        if confidence >= 95.0 and evidence_count >= 3 and len(token) >= 3:
            return True

    if len(tokens) <= 2 and confidence >= 94.0 and evidence_count >= 4:
        return True

    if ("?" in text or "!" in text) and confidence >= 88.0 and evidence_count >= 2:
        return True

    return False


def _should_drop_short_subtitle_candidate(text: str, normalized_text: str, confidence: float, evidence_count: int) -> bool:
    tokens = [token for token in normalized_text.split(" ") if token]
    if not tokens:
        return True
    if len(tokens) >= 3:
        return False

    if _is_obvious_short_subtitle(text, normalized_text, confidence, evidence_count):
        return False

    alnum_chars = len(re.findall(r"[a-z0-9]", normalized_text, flags=re.IGNORECASE))
    if alnum_chars <= 2:
        return True

    if len(tokens) == 1:
        token = re.sub(r"[^a-z0-9]+", "", tokens[0].lower())
        if len(token) <= 2:
            return True
        if confidence < 90.0 and evidence_count < 3:
            return True

    if len(tokens) == 2 and alnum_chars <= 5 and confidence < 90.0 and evidence_count < 3:
        return True

    return False


def build_segments(
    ocr_results: list[dict[str, Any]],
    similarity_threshold: float,
    merge_gap_seconds: float,
    hard_reset_gap_seconds: float,
    min_text_length: int,
    min_confidence: float,
) -> list[dict[str, Any]]:
    stable_events: list[dict[str, Any]] = []

    for row in ocr_results:
        text, line_confidence = _build_text_from_detected_lines(
            row,
            min_text_length=min_text_length,
            min_line_confidence=min_confidence,
        )
        confidence = float(line_confidence) if line_confidence is not None else float(row.get("confidence", 0.0))
        if confidence < min_confidence:
            continue

        normalized = normalize_text(text)
        if len(normalized) < min_text_length:
            continue
        if is_mostly_symbols(normalized):
            continue

        stable_events.append(
            {
                "timestamp": float(row["timestamp"]),
                "text": text.strip(),
                "normalized_text": normalized,
                "confidence": confidence,
                "frame": row.get("frame", ""),
            }
        )

    if not stable_events:
        return []

    stable_events.sort(key=lambda item: item["timestamp"])

    segments: list[dict[str, Any]] = []
    current = {
        "start": stable_events[0]["timestamp"],
        "end": stable_events[0]["timestamp"],
        "events": [dict(stable_events[0])],
        "confidences": [stable_events[0]["confidence"]],
        "frames": [stable_events[0]["frame"]],
    }

    for event in stable_events[1:]:
        gap = event["timestamp"] - current["end"]
        should_merge = gap <= merge_gap_seconds and _event_fits_segment(
            event,
            current["events"],
            similarity_threshold=similarity_threshold,
        )
        should_reset = gap > hard_reset_gap_seconds

        if should_merge and not should_reset:
            current["end"] = event["timestamp"]
            current["events"].append(dict(event))
            current["confidences"].append(event["confidence"])
            current["frames"].append(event["frame"])
        else:
            segments.append(current)
            current = {
                "start": event["timestamp"],
                "end": event["timestamp"],
                "events": [dict(event)],
                "confidences": [event["confidence"]],
                "frames": [event["frame"]],
            }

    segments.append(current)

    for segment in segments:
        confidences = [float(value) for value in segment.get("confidences", [])]
        consensus = _pick_consensus_event(segment.get("events", []))
        segment["text"] = consensus["text"]
        segment["normalized_text"] = consensus["normalized_text"]
        segment["event_count"] = len(segment.get("events", []))
        segment.pop("events", None)
        if not confidences:
            segment["avg_confidence"] = 0.0
            segment["max_confidence"] = 0.0
            continue
        segment["avg_confidence"] = round(sum(confidences) / len(confidences), 2)
        segment["max_confidence"] = round(max(confidences), 2)

    return segments


def build_subtitles(
    segments: list[dict[str, Any]],
    min_duration: float,
    max_duration: float,
) -> list[SubtitleItem]:
    subtitles: list[SubtitleItem] = []

    for segment in segments:
        start = float(segment["start"])
        end = float(segment["end"])

        duration = end - start
        if duration < min_duration:
            end = start + min_duration
        if (end - start) > max_duration:
            end = start + max_duration

        subtitles.append(SubtitleItem(start=round(start, 3), end=round(end, 3), text=segment["text"]))

    return subtitles


def consolidate_subtitle_candidates(
    segments: list[dict[str, Any]],
    min_duration: float,
    max_duration: float,
    min_candidate_confidence: float,
    similarity_threshold: float,
    merge_gap_seconds: float,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    repeated_noise_prefixes = detect_repeated_prefix_noise([str(seg.get("text", "")) for seg in segments])

    prepared: list[dict[str, Any]] = []
    noise_candidates: list[dict[str, Any]] = []

    for segment in segments:
        confidence = float(segment.get("avg_confidence", 0.0))
        if confidence < min_candidate_confidence:
            continue

        raw_text = str(segment.get("text", ""))
        cleaned_text, noise_fragments = extract_noise_fragments(raw_text, repeated_noise_prefixes)
        cleaned_text = _clean_consensus_text(cleaned_text)

        start = float(segment["start"])
        end = float(segment["end"])
        if end <= start:
            end = start + min_duration

        if noise_fragments:
            noise_candidates.append(
                {
                    "start": round(start, 3),
                    "end": round(end, 3),
                    "text": " ".join(noise_fragments),
                    "confidence": round(confidence, 2),
                    "source": "noise",
                }
            )

        normalized_cleaned = normalize_text(cleaned_text)
        evidence_count = int(segment.get("event_count") or len(segment.get("frames", [])) or 1)
        if len(normalized_cleaned) < 2 or is_mostly_symbols(normalized_cleaned):
            continue
        if _should_drop_short_subtitle_candidate(cleaned_text, normalized_cleaned, confidence, evidence_count):
            noise_candidates.append(
                {
                    "start": round(start, 3),
                    "end": round(end, 3),
                    "text": cleaned_text,
                    "confidence": round(confidence, 2),
                    "source": "short_artifact",
                }
            )
            continue

        prepared.append(
            {
                "start": round(start, 3),
                "end": round(end, 3),
                "text": cleaned_text,
                "normalized_text": normalized_cleaned,
                "confidence": round(confidence, 2),
                "event_count": evidence_count,
            }
        )

    if not prepared:
        return [], _ensure_non_overlapping(noise_candidates, min_duration)

    prepared.sort(key=lambda row: (float(row["start"]), float(row["end"])))

    consolidated: list[dict[str, Any]] = []
    current = dict(prepared[0])
    current["confidences"] = [float(current["confidence"])]

    for candidate in prepared[1:]:
        gap = float(candidate["start"]) - float(current["end"])
        similarity = text_similarity(str(current["normalized_text"]), str(candidate["normalized_text"]))
        should_merge = gap <= merge_gap_seconds and similarity >= similarity_threshold

        if should_merge:
            current["end"] = max(float(current["end"]), float(candidate["end"]))
            current["confidences"].append(float(candidate["confidence"]))
            if len(candidate["text"]) > len(current["text"]) or float(candidate["confidence"]) > float(current["confidence"]):
                current["text"] = candidate["text"]
                current["normalized_text"] = candidate["normalized_text"]
                current["confidence"] = candidate["confidence"]
            continue

        consolidated.append(current)
        current = dict(candidate)
        current["confidences"] = [float(current["confidence"])]

    consolidated.append(current)

    result: list[dict[str, Any]] = []
    for row in consolidated:
        start = float(row["start"])
        end = float(row["end"])
        duration = end - start
        if duration < min_duration:
            end = start + min_duration
        if (end - start) > max_duration:
            end = start + max_duration

        confidences = [float(value) for value in row.get("confidences", [])]
        avg_conf = round(sum(confidences) / len(confidences), 2) if confidences else float(row["confidence"])

        result.append(
            {
                "start": round(start, 3),
                "end": round(end, 3),
                "text": row["text"],
                "confidence": round(avg_conf, 2),
                "source": "subtitle",
            }
        )

    resolved_main = _ensure_non_overlapping(result, min_duration)
    resolved_noise = _ensure_non_overlapping(noise_candidates, min_duration)
    return resolved_main, resolved_noise


def subtitles_to_json_payload(items: list[SubtitleItem]) -> list[dict[str, Any]]:
    return [asdict(item) for item in items]
