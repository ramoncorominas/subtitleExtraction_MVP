from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import imageio_ffmpeg


@dataclass(slots=True)
class DependencyStatus:
    name: str
    source: str
    path: Optional[str]
    available: bool
    note: str = ""


def _windows_binary_name(name: str) -> str:
    return f"{name}.exe"


def _which(binary_name: str) -> Optional[str]:
    return shutil.which(binary_name)


def _app_binary_path(app_bin_dir: Path, binary_name: str) -> Path:
    return app_bin_dir / binary_name


def _ensure_app_bin_dir(app_bin_dir: Path) -> None:
    app_bin_dir.mkdir(parents=True, exist_ok=True)


def resolve_ffmpeg(app_bin_dir: Path, allow_bootstrap: bool = True) -> DependencyStatus:
    system_path = _which(_windows_binary_name("ffmpeg"))
    if system_path:
        return DependencyStatus(name="ffmpeg", source="system", path=system_path, available=True)

    app_path = _app_binary_path(app_bin_dir, _windows_binary_name("ffmpeg"))
    if app_path.exists():
        return DependencyStatus(name="ffmpeg", source="app", path=str(app_path), available=True)

    if not allow_bootstrap:
        return DependencyStatus(name="ffmpeg", source="missing", path=None, available=False, note="FFmpeg not found")

    _ensure_app_bin_dir(app_bin_dir)

    # imageio-ffmpeg downloads a prebuilt ffmpeg binary from curated, versioned sources.
    downloaded = Path(imageio_ffmpeg.get_ffmpeg_exe())
    shutil.copy2(downloaded, app_path)

    return DependencyStatus(name="ffmpeg", source="downloaded", path=str(app_path), available=True)


def _run_silent_tesseract_install() -> bool:
    # Winget packages are signed and validated by the package manager.
    command = [
        "winget",
        "install",
        "--id",
        "UB-Mannheim.TesseractOCR",
        "-e",
        "--silent",
        "--accept-package-agreements",
        "--accept-source-agreements",
    ]
    result = subprocess.run(command, capture_output=True, text=True)
    return result.returncode == 0


def resolve_tesseract(app_bin_dir: Path, allow_bootstrap: bool = True) -> DependencyStatus:
    system_path = _which(_windows_binary_name("tesseract"))
    if system_path:
        return DependencyStatus(name="tesseract", source="system", path=system_path, available=True)

    app_path = _app_binary_path(app_bin_dir, _windows_binary_name("tesseract"))
    if app_path.exists():
        return DependencyStatus(name="tesseract", source="app", path=str(app_path), available=True)

    if not allow_bootstrap:
        return DependencyStatus(name="tesseract", source="missing", path=None, available=False, note="Tesseract not found")

    installed = _run_silent_tesseract_install()
    if installed:
        system_path_after = _which(_windows_binary_name("tesseract"))
        if system_path_after:
            return DependencyStatus(name="tesseract", source="winget", path=system_path_after, available=True)

    return DependencyStatus(
        name="tesseract",
        source="missing",
        path=None,
        available=False,
        note="Auto-bootstrap failed. Install Tesseract manually or provide --tesseract-cmd.",
    )


def resolve_runtime_dependencies(
    app_bin_dir: Path,
    allow_bootstrap: bool,
    forced_tesseract_cmd: Optional[str] = None,
    forced_ffmpeg_cmd: Optional[str] = None,
) -> dict[str, DependencyStatus]:
    ffmpeg = DependencyStatus(name="ffmpeg", source="forced", path=forced_ffmpeg_cmd, available=bool(forced_ffmpeg_cmd))
    tesseract = DependencyStatus(name="tesseract", source="forced", path=forced_tesseract_cmd, available=bool(forced_tesseract_cmd))

    if not ffmpeg.available:
        ffmpeg = resolve_ffmpeg(app_bin_dir=app_bin_dir, allow_bootstrap=allow_bootstrap)

    if not tesseract.available:
        tesseract = resolve_tesseract(app_bin_dir=app_bin_dir, allow_bootstrap=allow_bootstrap)

    return {
        "ffmpeg": ffmpeg,
        "tesseract": tesseract,
    }
