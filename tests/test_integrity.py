from __future__ import annotations

import json
from pathlib import Path

import pytest

from quran_etl.transform import build_graph
from quran_etl.verify import verify_full, verify_min

from .support import (
    EXPECTED_TINY_COUNTS,
    emit_twelve_surah_datasets,
    make_settings,
    twelve_surah_metadata,
    twelve_surah_text,
)


def _rewrite(path: Path, mutate) -> None:
    value = json.loads(path.read_text(encoding="utf-8"))
    mutate(value)
    path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")


def test_numeric_membership_crosses_ten_boundary(tmp_path: Path):
    settings, graph = emit_twelve_surah_datasets(tmp_path)
    ayah = graph["ayah_by_key"]["10:2"]
    assert ayah.page == 10
    assert ayah.parents == {
        "surah": "surah:010",
        "juz": "juz:02",
        "manzil": "manzil:02",
        "ruku": "ruku:010",
        "hizb": "hizb:02",
        "rub": "rub:005",
        "page": "page:010",
    }
    assert graph["juzs"][1].child_ids["hizb"] == ["hizb:02"]
    assert graph["hizbs"][1].child_ids["rub"] == [
        "rub:005", "rub:006", "rub:007", "rub:008"
    ]
    assert graph["pages"][9].parent_ids == []
    assert verify_full(settings.data_dir, settings, EXPECTED_TINY_COUNTS) == []


def test_transform_rejects_missing_configured_bismillah(tmp_path: Path):
    text = twelve_surah_text()
    text[(10, 1)] = "نَصٌّ بِلَا بَسْمَلَةٍ"
    with pytest.raises(ValueError, match="10:1"):
        build_graph(twelve_surah_metadata(), text, make_settings(tmp_path))


def test_full_verifier_rejects_semantic_corruption(tmp_path: Path):
    settings, _ = emit_twelve_surah_datasets(tmp_path)
    ayah_path = settings.data_dir / "ayah" / "010_002.json"
    original_ayah = ayah_path.read_text(encoding="utf-8")
    _rewrite(ayah_path, lambda value: value["parents"].update(juz="juz:01"))
    assert any("parent map" in error for error in verify_full(settings.data_dir, settings, EXPECTED_TINY_COUNTS))
    ayah_path.write_text(original_ayah, encoding="utf-8")
    _rewrite(ayah_path, lambda value: value.update(page=1))
    assert any("page scalar" in error for error in verify_full(settings.data_dir, settings, EXPECTED_TINY_COUNTS))


def test_full_verifier_rejects_payload_and_stale_file_corruption(tmp_path: Path):
    settings, _ = emit_twelve_surah_datasets(tmp_path)
    surah_path = settings.data_dir / "surah" / "010.json"
    original = surah_path.read_text(encoding="utf-8")
    _rewrite(surah_path, lambda value: value["child_ids"]["ayah"].__setitem__(0, "10:1"))
    assert any("ayah child IDs" in error for error in verify_full(settings.data_dir, settings, EXPECTED_TINY_COUNTS))
    surah_path.write_text(original, encoding="utf-8")
    _rewrite(surah_path, lambda value: value.pop("ayahs"))
    assert any("missing inline ayahs" in error for error in verify_full(settings.data_dir, settings, EXPECTED_TINY_COUNTS))
    surah_path.write_text(original, encoding="utf-8")
    (settings.data_dir / "surah" / "999.json").write_text("{}", encoding="utf-8")
    assert any("file set mismatch" in error for error in verify_full(settings.data_dir, settings, EXPECTED_TINY_COUNTS))


def test_min_verifier_rejects_parent_and_short_key_corruption(tmp_path: Path):
    settings, _ = emit_twelve_surah_datasets(tmp_path)
    root = settings.data_dir
    ayah_path = root / "ayah" / "010_002.min.json"
    original = ayah_path.read_text(encoding="utf-8")
    _rewrite(ayah_path, lambda value: value["ps"].update(j="juz:01"))
    assert any("min parent map" in error for error in verify_min(root, settings, EXPECTED_TINY_COUNTS))
    ayah_path.write_text(original, encoding="utf-8")
    _rewrite(ayah_path, lambda value: value.update(unexpected=True))
    assert any("invalid short keys" in error for error in verify_min(root, settings, EXPECTED_TINY_COUNTS))


def test_min_range_extras_use_documented_short_keys(tmp_path: Path):
    settings, _ = emit_twelve_surah_datasets(tmp_path)
    root = settings.data_dir
    assert "sc" in json.loads((root / "juz" / "01.min.json").read_text(encoding="utf-8"))
    ruku = json.loads((root / "ruku" / "010.min.json").read_text(encoding="utf-8"))
    assert "sh" in ruku
    assert "surah" not in ruku and "surah_id" not in ruku
