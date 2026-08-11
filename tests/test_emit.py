"""End-to-end smoke test: a tiny two-sura fixture."""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path
from textwrap import dedent

from quran_etl import transform
from quran_etl.config import Settings
from quran_etl.emit import emit


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


def _fake_metadata() -> dict:
    return {
        "suras": [
            {"index": "1", "ayas": "3", "start": "0", "name": "x", "tname": "A",
             "ename": "B", "type": "Meccan", "order": "1", "rukus": "1"},
            {"index": "2", "ayas": "3", "start": "3", "name": "y", "tname": "C",
             "ename": "D", "type": "Medinan", "order": "2", "rukus": "2"},
        ],
        "juzs": [{"index": "1", "sura": "1", "aya": "1"}],
        "hizbs": [{"index": "1", "sura": "1", "aya": "1"}],
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
        (2, 3): "لَا رَيْبَ ۞ فِيهِ",
    }


def test_end_to_end_emit(tmp_path: Path):
    settings = _settings(tmp_path)
    settings.data_dir.mkdir()
    settings.raw_dir.mkdir()

    g = transform.build_graph(_fake_metadata(), _fake_text(), settings)
    manifest = emit(g, settings)["full"]

    # Surah count
    surahs = json.loads((settings.data_dir / "surah" / "index.json").read_text(encoding="utf-8"))
    assert len(surahs) == 2

    # Ayah files
    a1 = json.loads((settings.data_dir / "ayah" / "001_001.json").read_text(encoding="utf-8"))
    assert a1["text"] == "بِسْمِ ٱللَّهِ ٱلرَّحْمَٰنِ ٱلرَّحِيمِ"
    assert a1["parents"]["surah"] == "surah:001"

    # Bismillah should be stripped from surah 2 (not exempt)
    a2_1 = json.loads((settings.data_dir / "ayah" / "002_001.json").read_text(encoding="utf-8"))
    assert "بِسْمِ" not in a2_1["text"]
    assert "بِّسْمِ" not in a2_1["text"]

    # Sajdah ayah 2:2 should be marked
    a2_2 = json.loads((settings.data_dir / "ayah" / "002_002.json").read_text(encoding="utf-8"))
    assert a2_2["sajda"] == "obligatory"

    # Juz covers 1:1 .. 2:3
    j1 = json.loads((settings.data_dir / "juz" / "01.json").read_text(encoding="utf-8"))
    assert j1["start_ayah"] == "1:1"
    assert j1["end_ayah"] == "2:3"
    assert j1["ayah_count"] == 6

    # Full tree
    full = json.loads((settings.data_dir / "quran.full.json").read_text(encoding="utf-8"))
    assert full["meta"]["ayat_count"] == 6
    assert full["meta"]["schema_version"] == 4
    assert len(full["surahs"]) == 2
    # Surah 1 has inline ayahs (denormalized)
    assert len(full["surahs"][0]["ayahs"]) == 3
    per_surah = json.loads((settings.data_dir / "surah" / "001.json").read_text(encoding="utf-8"))
    assert len(per_surah["ayahs"]) == 3
    # ayah_ids is still kept as a convenience summary
    assert full["surahs"][0]["ayah_ids"] == ["1:1", "1:2", "1:3"]
    # Sajdah has ayah_data
    saj = json.loads((settings.data_dir / "sajdah" / "01.json").read_text(encoding="utf-8"))
    assert saj["ayah_data"]["text"].startswith("ذَ")

    # Manifest
    assert "quran.full" in manifest
    index = json.loads((settings.data_dir / "index.json").read_text(encoding="utf-8"))
    assert index["version"] == 4
