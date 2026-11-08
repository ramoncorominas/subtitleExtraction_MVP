# Subtitle MVP

OCR-first pipeline that extracts burned-in subtitles from video frames and exports real text subtitles (`.srt` and `.vtt`) with a local HTML demo overlay.

## Workflow

The pipeline runs five stages:

1. Preparation
2. Information retrieval
3. Fix preparation
4. Generating fixes
5. Post-production

Each stage writes JSON artifacts so results can be reviewed without rerunning the full process.

## Documentation

- [Architecture summary](architecture_summary.md):
	concise stage-by-stage explanation with short code and JSON examples.

## Project structure

- `app/`: CLI and configuration
- `pipeline/`: stage logic and processing modules
- `models/`: data models
- `data/input/`: source video
- `data/output/`: generated artifacts
- `data/debug/`: debug exports
- `tests/`: focused unit tests

## Requirements

- Python 3.14+
- FFmpeg available in PATH
- Tesseract OCR installed

## Verify tools on Windows

Run these checks in `cmd` or PowerShell:

```bat
py --version
ffmpeg -version
tesseract --version
```

Expected result:

- each command prints version details
- if a command is missing, you will see a message similar to "not recognised" (cmd) or "CommandNotFoundException" (PowerShell)

## Automatic dependency bootstrap (for demo distribution)

The pipeline now resolves runtime tools automatically in this order:

1. system PATH
2. app-local binaries in `tools/bin/`
3. auto-bootstrap fallback

Auto-bootstrap behaviour:

- FFmpeg: downloaded through `imageio-ffmpeg` and copied to `tools/bin/ffmpeg.exe`
- Tesseract: attempts silent install through `winget` package `UB-Mannheim.TesseractOCR`

This means demo users can often run without manually installing both tools first.
If bootstrap cannot resolve Tesseract, pass the executable explicitly with `--tesseract-cmd`.

## Install missing tools (Windows)

### Python 3.14+

- Recommended: install from [python.org Windows downloads](https://www.python.org/downloads/windows/)
- During install, enable "Add Python to PATH"

### Tesseract OCR

Option 1 (recommended): UB Mannheim build

1. Download installer from [UB Mannheim Tesseract releases](https://github.com/UB-Mannheim/tesseract/wiki)
2. Install to default path: `C:\Program Files\Tesseract-OCR`
3. Reopen terminal and run:

```bat
tesseract --version
```

If it is still not found in PATH, run pipeline with explicit executable path:

```bat
py -m app.cli --video data/input/input.mp4 --tesseract-cmd "C:\Program Files\Tesseract-OCR\tesseract.exe"
```

### FFmpeg

Option 1: winget

```bat
winget install --id Gyan.FFmpeg -e
```

Option 2: manual install

1. Download FFmpeg build from [Gyan FFmpeg builds](https://www.gyan.dev/ffmpeg/builds/)
2. Extract and add the `bin` folder to PATH
3. Reopen terminal and run:

```bat
ffmpeg -version
```

## Python dependencies

Install dependencies in the existing virtual environment:

```bat
.venv\Scripts\activate
py -m pip install --upgrade pip
py -m pip install -r requirements.txt
```

## Run

```bat
.venv\Scripts\activate
py -m app.cli --video data/input/input.mp4
```

Optional arguments:

- `--output-dir data/output`
- `--debug-dir data/debug`
- `--sample-interval 0.5`
- `--start 0`
- `--end 23`
- `--lang spa`
- `--ocr-psm 6`
- `--min-ocr-confidence 65`
- `--no-color-processing`
- `--disable-roi-crop`
- `--no-secondary-roi`
- `--roi-y-start 0.7`
- `--roi-height-ratio 0.22`
- `--roi-x-margin-ratio 0.10`
- `--tesseract-cmd "C:\\Program Files\\Tesseract-OCR\\tesseract.exe"`
- `--ffmpeg-cmd "C:\\path\\to\\ffmpeg.exe"`
- `--no-auto-bootstrap`
- `--verbose`

Notes:

- `--start` and `--end` limit processing to a time window in seconds
- `--lang` sets Tesseract OCR language (for Spanish use `spa`)
- `--no-color-processing` uses only the original crop (disables grayscale/contrast/threshold/sharpen variants)
- `--disable-roi-crop` skips subtitle ROI crop and runs OCR on full sampled frames

Example with auto-bootstrap enabled (default):

```bat
.venv\Scripts\activate
py -m app.cli --video data/input/input.mp4
```

Example with explicit tool paths:

```bat
.venv\Scripts\activate
py -m app.cli --video data/input/input.mp4 --tesseract-cmd "C:\Program Files\Tesseract-OCR\tesseract.exe" --ffmpeg-cmd "C:\ffmpeg\bin\ffmpeg.exe"
```

## Example: pantomima.mp4 (0s to 23s, sample every 0.4s)

With color preprocessing and ROI crop enabled (recommended baseline):

```bat
.venv\Scripts\activate
py -m app.cli --video data/input/pantomima.mp4 --start 0 --end 23 --sample-interval 0.4 --lang spa --tesseract-cmd "C:\Program Files\Tesseract-OCR\tesseract.exe"
```

Without color preprocessing and without ROI crop:

```bat
.venv\Scripts\activate
py -m app.cli --video data/input/pantomima.mp4 --start 0 --end 23 --sample-interval 0.4 --lang spa --tesseract-cmd "C:\Program Files\Tesseract-OCR\tesseract.exe" --no-color-processing --disable-roi-crop
```

## Outputs

Main output files:

- `data/output/sampled_frames_index.json`
- `data/output/candidate_regions_mvp.json`
- `data/output/ocr_results_mvp.json`
- `data/output/subtitle_segments_mvp.json`
- `data/output/subtitle_candidates_mvp.json`
- `data/output/subtitles_mvp.json`
- `data/output/subtitles_mvp.srt`
- `data/output/subtitles_mvp.vtt`
- `data/output/subtitles_mvp_debug.json`
- `data/output/subtitle_review_text_mvp.txt`
- `data/output/subtitles_demo.html`

## Test

```bat
.venv\Scripts\activate
py -m pytest
```
