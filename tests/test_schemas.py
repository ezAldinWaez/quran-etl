from __future__ import annotations

import json
from pathlib import Path

from jsonschema import validate

from quran_etl.schemas_emit import _MODELS

from .support import emit_twelve_surah_datasets


def test_emitted_full_payloads_validate_against_public_schemas(tmp_path: Path):
    settings, _ = emit_twelve_surah_datasets(tmp_path)
    files = {
        "ayah": settings.data_dir / "ayah" / "001_001.json",
        "surah": settings.data_dir / "surah" / "001.json",
        "juz": settings.data_dir / "juz" / "01.json",
        "manzil": settings.data_dir / "manzil" / "01.json",
        "hizb": settings.data_dir / "hizb" / "01.json",
        "rub": settings.data_dir / "rub" / "001.json",
        "ruku": settings.data_dir / "ruku" / "001.json",
        "page": settings.data_dir / "page" / "001.json",
        "sajdah": settings.data_dir / "sajdah" / "01.json",
    }
    for name, path in files.items():
        validate(json.loads(path.read_text(encoding="utf-8")), _MODELS[name].model_json_schema())
