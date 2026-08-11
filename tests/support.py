from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from quran_etl.config import Settings
from quran_etl.emit import emit
from quran_etl.transform import build_graph

BISMILLAH = "بِسْمِ ٱللَّهِ ٱلرَّحْمَٰنِ ٱلرَّحِيمِ"
BISMILLAH_VARIANT = "بِّسْمِ ٱللَّهِ ٱلرَّحْمَٰنِ ٱلرَّحِيمِ"
EXPECTED_TINY_COUNTS = {
    "surah": 12,
    "ayah": 24,
    "juz": 2,
    "manzil": 2,
    "ruku": 12,
    "hizb": 2,
    "rub": 8,
    "page": 12,
    "sajdah": 1,
}


def make_settings(tmp_path: Path) -> Settings:
    config = tmp_path / "settings.yaml"
    config.write_text(
        """download:
  base_url: https://example.invalid
  timeout_seconds: 5
  max_retries: 2
  backoff_factor: 0
sources:
  metadata_path: /metadata.xml
  quran_text_post_url: /text
  quran_text_form: {quranType: uthmani, outType: txt-2}
output:
  data_dir: data
  raw_dir: raw
  indent: 2
  ensure_ascii: false
text:
  type: uthmani
  strip_bismillah_from_non_fatiha: true
  bismillah_exempt_surahs: [1, 9, 96]
  normal_form: NFC
logging:
  level: WARNING
""",
        encoding="utf-8",
    )
    settings = Settings.load(config)
    return replace(settings, data_dir=tmp_path / "data", raw_dir=tmp_path / "raw")


def twelve_surah_metadata() -> dict:
    surahs = [
        {
            "index": str(sura),
            "ayas": "2",
            "start": str((sura - 1) * 2),
            "name": f"سورة {sura}",
            "tname": f"Sura-{sura}",
            "ename": f"Sura {sura}",
            "type": "Meccan" if sura % 2 else "Medinan",
            "order": str(sura),
            "rukus": "1",
        }
        for sura in range(1, 13)
    ]
    quarter_starts = [(1, 1), (3, 1), (5, 1), (7, 1), (10, 1), (11, 1), (12, 1), (12, 2)]
    return {
        "suras": surahs,
        "juzs": [
            {"index": "1", "sura": "1", "aya": "1"},
            {"index": "2", "sura": "10", "aya": "1"},
        ],
        "hizbs": [
            {"index": "1", "sura": "1", "aya": "1"},
            {"index": "2", "sura": "10", "aya": "1"},
        ],
        "quarters": [
            {"index": str(index), "sura": str(sura), "aya": str(aya)}
            for index, (sura, aya) in enumerate(quarter_starts, 1)
        ],
        "manzils": [
            {"index": "1", "sura": "1", "aya": "1"},
            {"index": "2", "sura": "7", "aya": "1"},
        ],
        "rukus": [
            {"index": str(sura), "sura": str(sura), "aya": "1"}
            for sura in range(1, 13)
        ],
        "pages": [
            {"index": str(sura), "sura": str(sura), "aya": "1"}
            for sura in range(1, 13)
        ],
        "sajdas": [{"index": "1", "sura": "10", "aya": "2", "type": "recommended"}],
    }


def twelve_surah_text() -> dict[tuple[int, int], str]:
    verses: dict[tuple[int, int], str] = {}
    for sura in range(1, 13):
        if sura == 1:
            first = BISMILLAH
        elif sura == 9:
            first = "بَرَاءَةٌ"
        else:
            prefix = BISMILLAH_VARIANT if sura in {10, 11} else BISMILLAH
            first = f"{prefix} نَصُّ السُّورَةِ {sura}"
        verses[(sura, 1)] = first
        verses[(sura, 2)] = f"الْآيَةُ الثَّانِيَةُ {sura}"
    return verses


def emit_twelve_surah_datasets(tmp_path: Path):
    settings = make_settings(tmp_path)
    graph = build_graph(twelve_surah_metadata(), twelve_surah_text(), settings)
    graph["provenance"] = {
        "metadata": {"content_sha256": "a" * 64},
        "text": {"content_sha256": "b" * 64},
    }
    emit(graph, settings, include_full=True, include_minified=True)
    return settings, graph
