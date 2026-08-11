"""Smoke tests for the minified JSON emitter."""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path
from textwrap import dedent

from quran_etl import transform
from quran_etl.config import Settings
from quran_etl.emit import (
    _minify_ayah_dict,
    emit,
)


def _settings(tmp_path: Path) -> Settings:
    cfg = tmp_path / "cfg.yaml"
    cfg.write_text(
        dedent(
            """\
            download:
              base_url: https://example.invalid
            sources:
              metadata_path: /meta
              quran_text_post_url: /text
              quran_text_form: {quranType: uthmani, outType: txt-2}
            output:
              data_dir: data
              raw_dir: raw
            text:
              type: uthmani
              strip_bismillah_from_non_fatiha: true
              bismillah_exempt_surahs: [1, 9, 96]
              normal_form: NFC
            logging:
              level: WARNING
            """
        ),
        encoding="utf-8",
    )
    s = Settings.load(cfg)
    return replace(s, data_dir=tmp_path / "data", raw_dir=tmp_path / "raw")


def _data_root(settings: Settings) -> Path:
    return settings.data_dir


def _fake_metadata() -> dict:
    return {
        "suras": [
            {"index": "1", "ayas": "3", "start": "0", "name": "x", "tname": "A",
             "ename": "B", "type": "Meccan", "order": "1", "rukus": "1"},
            {"index": "2", "ayas": "3", "start": "3", "name": "y", "tname": "C",
             "ename": "D", "type": "Medinan", "order": "2", "rukus": "2"},
        ],
        "juzs": [{"index": "1", "sura": "1", "aya": "1"}],
        "hizbs": [
            # Note: in real metadata, hizbs are derived from quarters (4 per hizb)
            # — we include one here for fixture completeness.
            {"index": "1", "sura": "1", "aya": "1"},
        ],
        "quarters": [
            {"index": "1", "sura": "1", "aya": "1"},
            {"index": "2", "sura": "1", "aya": "2"},
            {"index": "3", "sura": "1", "aya": "3"},
            {"index": "4", "sura": "2", "aya": "1"},
        ],
        "manzils": [{"index": "1", "sura": "1", "aya": "1"}],
        "rukus": [
            {"index": "1", "sura": "1", "aya": "1"},
            {"index": "2", "sura": "2", "aya": "1"},
        ],
        "pages": [{"index": "1", "sura": "1", "aya": "1"}],
        "sajdas": [{"index": "1", "sura": "2", "aya": "2", "type": "obligatory"}],
    }


def _fake_text() -> dict[tuple[int, int], str]:
    return {
        (1, 1): "بِسْمِ ٱللَّهِ ٱلرَّحْمَٰنِ ٱلرَّحِيمِ",
        (1, 2): "ٱلْحَمْدُ لِلَّهِ",
        (1, 3): "رَبِّ ٱلْعَـٰلَمِينَ",
        (2, 1): "بِّسْمِ ٱللَّهِ ٱلرَّحْمَٰنِ ٱلرَّحِيمِ ٱلٓمٓ",
        (2, 2): "ذَٰلِكَ ٱلْكِتَـٰبُ",
        (2, 3): "لَا رَيْبَ",
    }


def test_minify_ayah_short_keys():
    a = {
        "key": "1:1",
        "id": "ayah:1:1",
        "sura": 1, "aya": 1, "global_id": 1,
        "text": "بِسْمِ",
        "text_raw": "بِسْمِ",
        "text_clean": "بسم",
        "char_count": 4, "word_count": 1,
        "sajda": None, "page": 1,
        "parents": {"surah": "surah:001", "juz": "juz:01"},
    }
    out = _minify_ayah_dict(a)
    # Short keys present
    assert "k" in out and "t" in out and "tc" in out and "p" in out and "ps" in out
    # No dropped fields
    assert "id" not in out
    assert "sura" not in out
    assert "aya" not in out
    assert "global_id" not in out
    assert "text_raw" not in out
    assert "char_count" not in out
    assert "word_count" not in out
    # parents map short codes
    assert out["ps"] == {"s": "surah:001", "j": "juz:01"}


def test_minify_sajda_enum_to_one_char():
    a = {
        "key": "1:1", "id": "ayah:1:1", "sura": 1, "aya": 1, "global_id": 1,
        "text": "x", "text_raw": "x", "text_clean": "x",
        "char_count": 1, "word_count": 1,
        "sajda": "obligatory", "page": 1,
        "parents": {},
    }
    out = _minify_ayah_dict(a)
    assert out["sj"] == "o"
    a["sajda"] = "recommended"
    out2 = _minify_ayah_dict(a)
    assert out2["sj"] == "r"


def test_minify_preserves_arabic_text():
    a = {
        "key": "1:1", "id": "ayah:1:1", "sura": 1, "aya": 1, "global_id": 1,
        "text": "بِسْمِ ٱللَّهِ",
        "text_raw": "بِسْمِ ٱللَّهِ",
        "text_clean": "بسم ٱلله",
        "char_count": 0, "word_count": 0,
        "sajda": None, "page": 1,
        "parents": {},
    }
    out = _minify_ayah_dict(a)
    assert out["t"] == "بِسْمِ ٱللَّهِ"
    assert out["tc"] == "بسم ٱلله"


def test_emit_min_end_to_end(tmp_path: Path):
    settings = _settings(tmp_path)
    settings.data_dir.mkdir()
    settings.raw_dir.mkdir()

    g = transform.build_graph(_fake_metadata(), _fake_text(), settings)
    manifest = emit(g, settings, include_full=False, include_minified=True)["minified"]
    data = _data_root(settings)

    # Manifest points to the paired minified indexes under data/
    assert manifest["surah"].name == "index.min.json"
    assert manifest["surah"].parent.name == "surah"
    assert manifest["quran.full"].name == "quran.full.min.json"

    # Per-scope directory layout: surah/001.min.json, 002.min.json
    s1 = json.loads((data / "surah" / "001.min.json").read_text(encoding="utf-8"))
    assert "i" in s1 and "k" in s1 and "na" in s1 and "a" in s1
    assert "name_arabic" not in s1
    assert "revelation_order" not in s1
    assert "bismillah_pretext" not in s1
    assert "ayah_ids" not in s1
    assert "parent_ids" not in s1
    assert "child_ids" not in s1
    # Inline ayahs are minified
    assert len(s1["a"]) == 3
    a0 = s1["a"][0]
    assert a0["k"] == "1:1"
    assert a0["t"] == "بِسْمِ ٱللَّهِ ٱلرَّحْمَٰنِ ٱلرَّحِيمِ"
    assert a0["ps"]["s"] == "surah:001"

    # Per-ayah files: 001_001.min.json
    a1 = json.loads((data / "ayah" / "001_001.min.json").read_text(encoding="utf-8"))
    assert a1["k"] == "1:1"
    assert "sura" not in a1
    assert "global_id" not in a1
    assert a1["ps"]["s"] == "surah:001"

    # Sajdah file: 01.min.json
    s0 = json.loads((data / "sajdah" / "01.min.json").read_text(encoding="utf-8"))
    assert s0["t"] == "o"  # obligatory -> "o"
    assert s0["sh"] == "surah:002"
    assert s0["ad"]["k"] == "2:2"
    # Ayah dropped fields
    assert "id" not in s0["ad"]

    # Per-scope indexes exist
    for scope in ("surah", "juz", "manzil", "ruku", "hizb", "rub", "page", "sajdah", "ayah"):
        idx_path = data / scope / "index.min.json"
        assert idx_path.exists(), f"missing {idx_path}"
        idx = json.loads(idx_path.read_text(encoding="utf-8"))
        assert isinstance(idx, list) and len(idx) > 0

    # Full tree
    full = json.loads(manifest["quran.full"].read_text(encoding="utf-8"))
    assert full["m"]["ac"] == 6
    assert full["m"]["sc"] == 2
    assert full["m"]["sv"] == 4
    assert "s" in full and "j" in full and "sj" in full
    for k in ("ac", "sc", "jc", "mnc", "rc", "hc", "rbc", "pc", "sac"):
        assert k in full["m"]
    index = json.loads((data / "index.min.json").read_text(encoding="utf-8"))
    assert index["v"] == 4


def test_minified_files_are_whitespace_compact(tmp_path: Path):
    settings = _settings(tmp_path)
    settings.data_dir.mkdir()
    settings.raw_dir.mkdir()
    g = transform.build_graph(_fake_metadata(), _fake_text(), settings)
    emit(g, settings, include_full=False, include_minified=True)
    data = _data_root(settings)
    for path in data.rglob("*.min.json"):
        txt = path.read_text(encoding="utf-8")
        assert ", " not in txt
        assert ": " not in txt


def test_purge_json_files_selects_variant_and_preserves_readmes(tmp_path: Path):
    from quran_etl.cli import _purge_json_files

    root = tmp_path / "data"
    (root / "surah").mkdir(parents=True)
    (root / "ayah").mkdir(parents=True)
    # Drop some JSON and some markdown
    (root / "surah" / "001.json").write_text("{}")
    (root / "surah" / "001.min.json").write_text("{}")
    (root / "ayah" / "001_001.min.json").write_text("{}")
    (root / "surah" / "README.md").write_text("# docs")
    (root / "README.md").write_text("# root")
    (root / ".gitkeep").write_text("")

    _purge_json_files(root, minified=True)

    # Only minified JSON is gone
    assert (root / "surah" / "001.json").exists()
    assert not (root / "surah" / "001.min.json").exists()
    assert not (root / "ayah" / "001_001.min.json").exists()
    # All .md / .gitkeep preserved
    assert (root / "surah" / "README.md").exists()
    assert (root / "README.md").exists()
    assert (root / ".gitkeep").exists()
    # Directories that still hold docs are kept (surah has README.md);
    # directories that became empty (ayah) are removed.
    assert (root / "surah").is_dir()              # README inside — kept
    assert not (root / "ayah").exists()            # became empty — removed
