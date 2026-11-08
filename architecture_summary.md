# Subtitle MVP Architecture Summary

This document explains how the pipeline is built, stage by stage, with short
code excerpts and compact JSON examples.

The goal is to make the flow understandable without reading the whole codebase.
All examples are intentionally small and omit obvious details for clarity.

## End-to-end flow

The pipeline runs five ordered stages. Each stage writes artifacts that become
inputs for the next stage.

~~~python
frame_index = stage_preparation(config)
_, ocr_rows = stage_information_retrieval(config, frame_index)
segments = stage_fix_preparation(config, ocr_rows)
subtitle_candidates, noise_candidates = stage_generating_fixes(
    config, segments
)
artifacts = stage_post_production(
    config, subtitle_candidates, noise_candidates
)
~~~

## Stage 1: preparation (video sampling)

Stage 1 opens the input video, samples frames by time interval, and writes a
frame index JSON. This gives deterministic timestamps for all later OCR work.

~~~python
capture = cv2.VideoCapture(str(video_path))
fps = capture.get(cv2.CAP_PROP_FPS) or 0.0
step = max(1, int(round(sample_interval_seconds * fps)))
sampling_indices = set(range(start_frame, end_frame + 1, step))

if frame_number in sampling_indices:
    timestamp = frame_number / fps
    filename = f"frame_{sample_number:0{index_padding}d}.jpg"
    cv2.imwrite(str(sampled_frames_dir / filename), frame)
~~~

Example output shape:

~~~json
{
  "sample_interval_seconds": 0.4,
  "fps": 25.0,
  "frames": [
    {"index": 0, "timestamp": 0.0, "path": ".../frame_000.jpg"},
    {"index": 1, "timestamp": 0.4, "path": ".../frame_001.jpg"}
  ]
}
~~~

## Stage 2: information retrieval (OCR)

For this documentation profile, OCR is full-frame and no color effects are
applied. Each sampled frame is OCR-processed and converted into line-level text
plus a frame confidence score.

~~~python
for frame_record in frame_index["frames"]:
    frame = cv2.imread(str(config.output_dir / frame_record["path"]))
    data = pytesseract.image_to_data(
        frame,
        output_type=pytesseract.Output.DICT,
        config="--oem 3 --psm 6",
        lang="spa",
    )
    _, _, text_lines = _extract_text_confidence(data)
    frame_confidence = _line_driven_confidence(text_lines)
~~~

Low and high confidence can coexist in the same frame:

~~~json
{
  "timestamp": 0.0,
  "text_lines": [
    {"text": "I \" a S >-<(017)", "confidence": 28.0},
    {"text": "+ = Ú o n", "confidence": 19.4},
    {"text": "Si la rumba y el bakalao pudieron entenderse", "confidence": 93.4}
  ],
  "confidence": 94.7
}
~~~

## Stage 3: fix preparation (stability + segmentation)

Stage 3 removes weak OCR content and keeps only stable entries. Then it merges
similar text events across nearby timestamps into segments.

### 3.1 Keep stable entries

~~~python
text, line_conf = _build_text_from_detected_lines(
    row, min_text_length, min_confidence
)
confidence = float(line_conf) if line_conf is not None else row["confidence"]
if confidence < min_confidence:
    continue
if len(normalize_text(text)) < min_text_length:
    continue
stable_events.append({"timestamp": row["timestamp"], "text": text})
~~~

### 3.2 Merge similar events into one segment

~~~python
gap = event["timestamp"] - current["end"]
should_merge = gap <= merge_gap_seconds and _event_fits_segment(
    event, current["events"], similarity_threshold
)
if should_merge:
    current["end"] = event["timestamp"]
    current["events"].append(dict(event))
else:
    segments.append(current)
~~~

Example segment shape:

~~~json
{
  "start": 0.0,
  "end": 4.0,
  "text": "Si la rumba y el bakalao pudieron entenderse...",
  "event_count": 11,
  "avg_confidence": 94.92
}
~~~

## Stage 4: generating fixes (candidate selection)

Stage 4 applies stricter filtering to decide which segments become subtitles.
It also keeps noise artifacts in a separate list for review.

~~~python
if confidence < min_candidate_confidence:
    continue
cleaned_text, noise_fragments = extract_noise_fragments(
    raw_text, repeated_noise_prefixes
)
if _should_drop_short_subtitle_candidate(
    cleaned_text, normalize_text(cleaned_text), confidence, evidence_count
):
    noise_candidates.append({"text": cleaned_text, "source": "short_artifact"})
    continue
~~~

Example candidate row:

~~~json
{
  "start": 22.8,
  "end": 29.2,
  "text": "CAMELA - Cuando zarpa el amor\\n(Música Sí, 2004)",
  "confidence": 93.12,
  "source": "subtitle"
}
~~~

## Stage 5: post-production (final exports)

Stage 5 converts candidates to final subtitle items and exports JSON, SRT, and
VTT files. It also creates the demo artifacts.

~~~python
json_rows = [
    {"start": row.start, "end": row.end, "text": row.text}
    for row in subtitles
]
write_json(subtitles_json, json_rows)
write_text(subtitles_srt, build_srt(subtitles))
write_text(subtitles_vtt, build_vtt(subtitles))
~~~

Final JSON output:

~~~json
[
  {"start": 0.0, "end": 4.0, "text": "Si la rumba y el bakalao..."},
  {"start": 22.8, "end": 29.2, "text": "CAMELA - Cuando zarpa el amor"},
  {"start": 30.0, "end": 37.6, "text": "¿Quién dijo que el himno...?"}
]
~~~

## Data contract between stages

- Stage 1 -> Stage 2: sampled frame index with timestamps.
- Stage 2 -> Stage 3: OCR rows with text lines and confidence.
- Stage 3 -> Stage 4: merged segments with stability/confidence context.
- Stage 4 -> Stage 5: subtitle candidates and noise candidates.

This staged contract makes debugging practical because each phase has explicit
JSON artifacts that can be inspected independently.