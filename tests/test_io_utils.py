from __future__ import annotations

from pathlib import Path

import pytest

from quran_etl.io_utils import atomic_write_text


def test_atomic_write_replaces_content_and_preserves_mode(tmp_path: Path):
    path = tmp_path / "value.json"
    path.write_text("old", encoding="utf-8")
    path.chmod(0o640)

    atomic_write_text(path, "new")

    assert path.read_text(encoding="utf-8") == "new"
    assert path.stat().st_mode & 0o777 == 0o640
    assert list(tmp_path.glob(".value.json.*")) == []


def test_atomic_write_failure_keeps_original_and_cleans_temp(tmp_path: Path, monkeypatch):
    path = tmp_path / "value.json"
    path.write_text("old", encoding="utf-8")

    def fail_fsync(_fd: int) -> None:
        raise OSError("simulated flush failure")

    monkeypatch.setattr("quran_etl.io_utils.os.fsync", fail_fsync)
    with pytest.raises(OSError, match="simulated"):
        atomic_write_text(path, "new")

    assert path.read_text(encoding="utf-8") == "old"
    assert list(tmp_path.glob(".value.json.*")) == []
