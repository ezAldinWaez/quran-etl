from __future__ import annotations

from pathlib import Path

import pytest

from quran_etl.config import Settings


def test_quoted_boolean_is_rejected(tmp_path: Path):
    path = tmp_path / "settings.yaml"
    path.write_text('output:\n  ensure_ascii: "false"\n', encoding="utf-8")
    with pytest.raises(ValueError, match="YAML boolean"):
        Settings.load(path)


def test_invalid_retry_and_duplicate_exemptions_are_rejected(tmp_path: Path):
    retry = tmp_path / "retry.yaml"
    retry.write_text("download:\n  max_retries: 0\n", encoding="utf-8")
    with pytest.raises(ValueError, match="max_retries"):
        Settings.load(retry)
    exemptions = tmp_path / "exemptions.yaml"
    exemptions.write_text("text:\n  bismillah_exempt_surahs: [1, 1]\n", encoding="utf-8")
    with pytest.raises(ValueError, match="duplicates"):
        Settings.load(exemptions)


def test_non_string_paths_are_rejected(tmp_path: Path):
    path = tmp_path / "settings.yaml"
    path.write_text("sources:\n  metadata_path: [bad]\n", encoding="utf-8")
    with pytest.raises(ValueError, match="metadata_path"):
        Settings.load(path)
