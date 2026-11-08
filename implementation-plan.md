# Simple MVP Plan: Subtitle Extraction

## Goal

Extract burned subtitle text and export a basic synchronised subtitle file for a demo, while following a minimal five-stage workflow.

## MVP scope

Keep it focused on the five stages:

- Preparation
- Information retrieval
- Fix preparation
- Generating fixes
- Post-production

Only include the simplest practical steps needed to produce readable subtitle output.

## Out of scope for MVP

Do not include:

- heavy multi-region classification models
- ASR-based correction or diarization alignment
- translation or summarisation pipelines
- complex scene-aware refinement loops
- large-scale review tooling

This MVP stays OCR-first and intentionally excludes speech recognition. Audio support can be added later as a separate iteration once the video-only subtitle flow is working.

## Minimal five-stage workflow

### 1. Preparation

- sample frames at a fixed interval (for example every 0.5 seconds)
- keep timestamp mapping for each sampled frame
- read the video and extract the frame stream
- save the sampled frames to disk so they can be reviewed visually
- prepare a simple lower-region ROI for subtitle detection

Output:

- sampled_frames_index.json
- sampled_frames/

### 2. Information retrieval

- focus on the lower third of the frame by default
- optionally detect a second nearby region for two-line subtitles
- run OCR on the selected subtitle regions
- save the OCR ROI crops or the processed frame crops for inspection
- apply basic text cleaning (trim spaces, remove obvious artefacts)
- keep this stage strictly visual and OCR-based for the MVP

Output:

- candidate_regions_mvp.json
- ocr_results_mvp.json
- frame_crops/

### 3. Fix preparation

- compare OCR results from nearby frames
- review the frame crops or sampled frames to confirm subtitle stability
- merge highly similar repeated text within a short time window
- reset the repeated-text cache when a new subtitle text appears or a longer gap is detected
- decide the start and end of each subtitle segment from stability in nearby samples

Output:

- subtitle_segments_mvp.json

### 4. Generating fixes

- build subtitle entries with start/end times and clean text
- save a structured JSON review file with the subtitle candidates for manual inspection
- save a plain-text version without timestamps for quick spelling and transcription review
- keep only a simple merged version for the demo

Output:

- subtitle_candidates_mvp.json
- subtitle_review_text_mvp.txt

### 5. Post-production

- export the final subtitle data in standard subtitle formats: SRT and VTT
- write a debug JSON copy for review
- keep the sampled frames and OCR crops alongside the subtitle output for quick manual verification
- generate a simple HTML demo page with a video player and a subtitle overlay layer
- expose the subtitle text in an ARIA live region so screen readers can announce subtitle changes
- keep the output simple and easy to check in the demo
- optionally export a second copy for later refinement

Output:

- subtitles_mvp.srt
- subtitles_mvp.vtt
- subtitles_mvp.json
- subtitles_mvp_debug.json
- subtitles_demo.html
- sampled_frames/
- frame_crops/

## Suggested tools

- OpenCV or FFmpeg for frame sampling
- Tesseract, EasyOCR, or PaddleOCR for text extraction
- rapidfuzz or difflib for text similarity
- a small HTML/JavaScript viewer for demo playback and subtitle overlay

## Demo success criteria

- extracted subtitles are mostly readable
- timings are roughly aligned with on-screen appearance
- duplicate lines are reasonably merged
- repeated text that appears later in the video is not accidentally merged with an earlier occurrence if it is clearly separate in time

## Minimal design note

This is intentionally a simple implementation of the five-stage workflow. It stays OCR-first to keep the demo usable and easy to deliver. Audio-based ASR can be added later as a separate refinement, after the visual subtitle pipeline is already working.

## Technical implementation plan

This implementation plan turns the MVP into a concrete Python project that can be built by an agent or a small team. The design follows a strict pipeline: each stage writes well-defined artefacts, and the next stage consumes those artefacts as its input. This keeps the workflow debuggable, modular, and easy to extend later.

### 1. Project structure

Use a small package-based structure so each responsibility has a single module:

```text
subtitle_mvp/
├── app/
│   ├── __init__.py
│   ├── config.py
│   ├── main.py
│   └── cli.py
├── pipeline/
│   ├── __init__.py
│   ├── stages.py
│   ├── io_utils.py
│   ├── frame_sampler.py
│   ├── roi_detector.py
│   ├── text_ocr.py
│   ├── subtitle_builder.py
│   ├── export.py
│   └── demo.py
├── models/
│   ├── __init__.py
│   ├── subtitle_item.py
│   └── frame_record.py
├── data/
│   ├── input/
│   ├── output/
│   └── debug/
├── tests/
│   ├── test_frame_sampling.py
│   ├── test_roi_detection.py
│   ├── test_ocr_cleaning.py
│   └── test_export.py
├── requirements.txt
├── .gitignore
├── README.md
└── .venv/
```

The implementation should keep all orchestration in one pipeline runner and leave the actual logic in focused modules. The runner coordinates the flow, while each module is responsible for one job only.

### 2. Pipeline flow and data contracts

The pipeline should be explicit and staged so each process consumes the output of the previous one.

1. Stage 1: Preparation
   - Input: source video file
   - Output: sampled frames, frame index, processed audio, ROI metadata
   - Module: frame_sampler.py + io_utils.py

2. Stage 2: Information retrieval
   - Input: sampled frames and processed audio
   - Output: OCR candidates, crop images, detected regions
   - Module: roi_detector.py + text_ocr.py

3. Stage 3: Fix preparation
   - Input: OCR and region evidence
   - Output: clean candidate blocks, grouped subtitle segments
   - Module: subtitle_builder.py

4. Stage 4: Generating fixes
   - Input: grouped segments
   - Output: subtitle entries with start/end timestamps and cleaned text
   - Module: subtitle_builder.py + export.py

5. Stage 5: Post-production
   - Input: final subtitle entries
   - Output: SRT, VTT, JSON, debug exports, HTML demo page
   - Module: export.py + demo.py

Each stage should write a structured JSON artifact so the project can be debugged without rerunning the whole pipeline.

### 3. Recommended Python libraries

Use a minimal, stable stack rather than a heavy ML framework:

- OpenCV (`opencv-python`): video reading, frame sampling, ROI extraction, resizing, thresholding, contours, and basic image cleanup
- NumPy: matrix transforms and simple operations on image arrays
- Pillow: image post-processing and crop handling
- Tesseract OCR (`pytesseract`): default OCR engine for the MVP and the clearest choice for a deterministic workflow
- FFmpeg: install as a system dependency and call it through subprocess for audio extraction and trimming; this is more reliable than a Python-only wrapper for large video files
- rapidfuzz: text similarity comparisons and duplicate detection
- pandas: optional but useful for timeline grouping and debugging candidate tables
- pydub: optional but helpful for audio filtering and exports if an audio-based future stage is added
- Flask or a static HTML/JavaScript viewer: for the demo page, a static HTML page is enough; a lightweight Flask server is only needed if the browser must load local JSON dynamically

Concrete implementation decision:

- default OCR engine: Tesseract via `pytesseract`
- default video processing: OpenCV
- default audio extraction: FFmpeg CLI
- default text similarity: `rapidfuzz.fuzz.ratio` and `SequenceMatcher` for fallback
- default export: custom JSON + custom SRT writer, with VTT generated from the same data model

This gives a stable MVP stack without over-engineering.

### 4. Environment setup

Create a dedicated project environment before any implementation work:

```bat
py -m venv .venv
.venv\Scripts\activate
py -m pip install --upgrade pip
py -m pip install -r requirements.txt
```

If the virtual environment is already active, then use the default Python command form instead of `py`.

The project should include a `requirements.txt` file listing the working versions of the libraries used. This should be kept in sync with the actual environment used for the final demo.

Suggested baseline requirements:

```txt
opencv-python>=4.9
numpy>=1.26
pytesseract>=0.3.10
Pillow>=10.0
rapidfuzz>=3.0
pandas>=2.0
pydub>=0.25
pytest>=8.0
```

The FFmpeg binary must also be installed on the system and available on the PATH, because OpenCV alone is not enough for reliable audio extraction and trimming.

### 5. Module responsibilities

#### frame_sampler.py

Responsibilities:

- open the source video
- sample frames at a fixed rate, such as every 0.5 seconds
- save a frame index with timestamp and filename
- keep a stable mapping between timestamps and frame paths
- write raw sampled frames to `data/output/sampled_frames/`

Suggested data schema:

```json
{
  "video": "input.mp4",
  "sample_interval_seconds": 0.5,
  "frames": [
    {"index": 0, "timestamp": 0.0, "path": "sampled_frames/frame_0000.jpg"}
  ]
}
```

#### roi_detector.py

Responsibilities:

- find subtitle-like regions in each sampled frame
- detect a lower-centre ROI for the main subtitle area
- optionally keep a second ROI for two-line subtitles
- return bounding boxes with confidence scoring

Decision rules:

- prefer the lower third of the frame
- accept a region only if its bounding box is below 70% of the frame height
- reject regions that are too small, too narrow, or too close to the top edge
- store the ROI metadata with the frame timestamp for debugging

#### text_ocr.py

Responsibilities:

- crop the ROI from each frame
- apply a small set of pre-processing variants, such as grayscale, contrast increase, sharpening, and thresholding
- run OCR on each variant
- return OCR text plus confidence values

Recommended OCR variants:

- original crop
- grayscale crop
- contrast-enhanced crop
- thresholded crop
- sharpened crop

Use at least one OCR pass on the processed crop and one on the original crop, then merge the best candidates by confidence and consistency.

#### subtitle_builder.py

Responsibilities:

- normalize text and remove obvious noise
- group nearby OCR detections into candidate subtitle blocks
- merge highly similar text within a short time window
- reject fragments that are too short or too noisy
- infer subtitle start and end times from surrounding frames

This module is the core of the MVP logic and should be deliberately small but strict.

#### export.py

Responsibilities:

- export final JSON
- generate SRT and VTT files
- write a debug JSON copy for human review
- keep a plain-text transcript for manual QA

#### demo.py

Responsibilities:

- create a simple HTML page with a video element and overlay subtitle layer
- load the final subtitle JSON or VTT file
- update the overlay text using JavaScript and the subtitle timing data
- keep the page easy to open locally without a backend service

For the MVP, a static HTML page plus JavaScript is the best choice. It keeps the demo simple and reliable.

### 6. Processing decisions and thresholds

These decisions reduce the risk of bad subtitle merges and false positives.

#### Sampling rate

- default sample interval: 0.5 seconds
- acceptable range: 0.25 to 1.0 seconds
- if the subtitle speed is very fast, use 0.25s for a denser check
- if the video is long and subtitle style is stable, 0.5s is a good default compromise

#### Region confidence and acceptance

- region must be within lower 30-40% of the frame height
- reject text regions if the height is under 15% of the frame height
- reject text if the OCR confidence is below 60 for a single pass
- accept the candidate if at least one processed variant is above 70 confidence and the text is stable for at least two nearby frames

#### OCR confidence rules

- use a minimum OCR confidence threshold of 65 to keep weak false positives out
- if two different OCR passes agree on the same text and both are above 60, accept it as a stronger result
- if the same text repeats in three or more adjacent frames, consider it stable and likely subtitle content
- if the OCR result changes too often in a short window, treat it as unstable and delay the merge

#### Merging criteria

- merge repeated text if same normalized text and gap is less than 2.5 seconds
- merge only when similarity is above 0.88 using normalized text comparison
- if the same phrase appears again after 10 seconds, treat it as a new subtitle event
- do not merge if the text differs materially in length or if the later phrase is a clearly different sentence

#### Discard criteria

Discard a candidate if any of the following are true:

- OCR text is shorter than 2 characters
- detected text is mostly punctuation or symbols
- text appears only once and has no temporal stability
- region is in the top area of the frame, is too small, or is decorative branding
- candidate text is log-like, social tags, or code-like text not consistent with subtitle rhythm
- text is duplicated across many different timestamps but has no real subtitle pattern

#### Timing rules

- subtitle start time: first timestamp when the text becomes stable in OCR
- subtitle end time: last timestamp before the text disappears or changes to a new line
- minimum subtitle duration: 0.8 seconds
- maximum subtitle duration: 10 seconds for the MVP unless the subtitle is clearly a long sentence or a slow-paced speaker
- if a subtitle segment is too short, merge with the nearest similar block if the time gap is small

### 7. Output artefacts and file naming

Each stage should write a predictable artifact set:

- `data/output/sampled_frames_index.json`
- `data/output/sampled_frames/`
- `data/output/processed_frames/`
- `data/output/processed_audio/`
- `data/output/frame_crops/`
- `data/output/candidate_regions_mvp.json`
- `data/output/ocr_results_mvp.json`
- `data/output/subtitle_segments_mvp.json`
- `data/output/subtitle_candidates_mvp.json`
- `data/output/subtitles_mvp.json`
- `data/output/subtitles_mvp.srt`
- `data/output/subtitles_mvp.vtt`
- `data/output/subtitles_mvp_debug.json`
- `data/output/subtitles_demo.html`

This structure makes the project easy to review and easy to hand off to a follow-up agent.

### 8. Demo strategy

The demo should be small, local, and easy to validate manually.

- use a sample video with a stable subtitle style and moderate contrast
- open the HTML page locally in a browser
- load the generated VTT or JSON subtitle file
- display the subtitle text as a transparent overlay on the video
- keep the ARIA live region active so the current subtitle is announced to screen readers
- allow a manual review of the side-by-side frame crops and OCR results

The goal is not a production web app. The goal is a clear, usable demo that proves the subtitle extraction pipeline works end to end.

### 9. Implementation order for an agent

The implementation should follow this order:

1. create the virtual environment and install dependencies
2. create the project structure and requirements.txt
3. implement video loading and frame sampling
4. implement ROI detection and OCR preprocessing
5. store OCR results and frame crops in JSON and disk files
6. implement candidate grouping and subtitle merging
7. implement SRT and VTT export
8. implement the HTML demo page and overlay logic
9. run a focused manual validation against a short sample video
10. iterate on thresholds and merge rules based on real output quality

This order keeps the pipeline stable and makes failures easy to isolate.

### 10. Good first-pass success criteria

The first viable version should satisfy all of the following:

- extracts readable subtitle text from a short test video
- preserves timestamps reasonably well
- merges stable repeated text only when it belongs to the same subtitle block
- avoids obvious false positives from decorative overlays or noise
- produces SRT and VTT files from the final subtitle list
- provides a working local demo page with overlay text and screen-reader-friendly output

This is a realistic MVP target and is the right level for an initial implementation. The module split, thresholds, and clear data contracts make it possible to expand later with ASR or refinement passes without rewriting the architecture.

This is intentionally a simple implementation of the five-stage workflow. It stays OCR-first to keep the demo usable and easy to deliver. Audio-based ASR can be added later as a separate refinement, after the visual subtitle pipeline is already working.
