@echo off
setlocal EnableDelayedExpansion

set "ROOT_DIR=%~dp0"
cd /d "%ROOT_DIR%"

if not exist ".venv\Scripts\activate.bat" (
    echo [error] Virtual environment not found at .venv\Scripts\activate.bat
    exit /b 1
)

set "VIDEO=%~1"
if "%VIDEO%"=="" set "VIDEO=data\input\cachititos.mp4"

if not exist "%VIDEO%" (
    echo [error] Video file not found: %VIDEO%
    exit /b 1
)

set "CLEAN_OUTPUT=N"
set /p "CLEAN_OUTPUT=Delete existing data\output before running? (y/N): "
if /i "%CLEAN_OUTPUT%"=="y" (
    if exist "data\output" (
        echo [subtitle-mvp] Cleaning data\output...
        rmdir /s /q "data\output"
        if errorlevel 1 (
            echo [error] Failed to delete data\output
            exit /b 1
        )
    )
)

if not exist "data\debug\tmp_tesseract" mkdir "data\debug\tmp_tesseract"

set "TESSDATA_PREFIX=%ROOT_DIR%tools\tessdata"
set "TEMP=%ROOT_DIR%data\debug\tmp_tesseract"
set "TMP=%TEMP%"

call ".venv\Scripts\activate.bat"
if errorlevel 1 (
    echo [error] Failed to activate virtual environment
    exit /b 1
)

echo [subtitle-mvp] Running full pipeline on %VIDEO%
python -m app.cli --video "%VIDEO%" --sample-interval 0.4 --lang spa --disable-roi-crop --no-color-processing
set "PIPELINE_EXIT=%ERRORLEVEL%"

if "%PIPELINE_EXIT%"=="0" (
    set "DEMO_HTML=%ROOT_DIR%data\output\stage-5-post-production\subtitles_demo.html"
    if exist "!DEMO_HTML!" (
        echo [subtitle-mvp] Opening demo in browser: !DEMO_HTML!
        start "" "!DEMO_HTML!"
    ) else (
        echo [warning] Demo HTML not found at !DEMO_HTML!
    )
) else (
    echo [warning] Pipeline exited with code %PIPELINE_EXIT%; demo was not opened.
)

exit /b %PIPELINE_EXIT%
