from pathlib import Path

from app.cli import build_default_output_dirs
from app.config import DEFAULT_DEBUG_DIR, DEFAULT_OUTPUT_DIR


def test_build_default_output_dirs_uses_main_roots() -> None:
    output_dir, debug_dir = build_default_output_dirs()

    assert isinstance(output_dir, Path)
    assert isinstance(debug_dir, Path)
    assert output_dir == DEFAULT_OUTPUT_DIR
    assert debug_dir == DEFAULT_DEBUG_DIR
    assert output_dir.name == "output"
    assert debug_dir.name == "debug"
