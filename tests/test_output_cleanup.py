from pathlib import Path

from pipeline.io_utils import clear_directory


def test_clear_directory_removes_existing_files(tmp_path: Path) -> None:
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    stale_file = output_dir / "old.txt"
    stale_file.write_text("stale", encoding="utf-8")
    nested_dir = output_dir / "nested"
    nested_dir.mkdir()
    (nested_dir / "keep.txt").write_text("keep", encoding="utf-8")

    clear_directory(output_dir)

    assert not stale_file.exists()
    assert not nested_dir.exists()
    assert output_dir.exists()
