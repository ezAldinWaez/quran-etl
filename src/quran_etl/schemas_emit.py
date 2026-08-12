"""Emit JSON Schema files for each public model."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from .io_utils import atomic_write_text
from .schemas import (
    Ayah,
    Hizb,
    Juz,
    Manzil,
    MinAyah,
    MinHizb,
    MinJuz,
    MinManzil,
    MinPage,
    MinRub,
    MinRuku,
    MinSajdah,
    MinSurah,
    Page,
    QuranFull,
    QuranFullMin,
    RootIndex,
    RootIndexMin,
    Rub,
    Ruku,
    Sajdah,
    ScopeIndex,
    ScopeIndexMin,
    Surah,
)

logger = logging.getLogger(__name__)

_DIALECT = "https://json-schema.org/draft/2020-12/schema"
_SCHEMA_BASE = "https://quran-etl.local/schemas"


_MODELS: dict[str, type[BaseModel]] = {
    "ayah": Ayah,
    "surah": Surah,
    "juz": Juz,
    "manzil": Manzil,
    "hizb": Hizb,
    "rub": Rub,
    "ruku": Ruku,
    "page": Page,
    "sajdah": Sajdah,
}

_PUBLIC_MODELS: dict[str, type[BaseModel]] = {
    **{f"{name}.schema.json": model for name, model in _MODELS.items()},
    "ayah.min.schema.json": MinAyah,
    "surah.min.schema.json": MinSurah,
    "juz.min.schema.json": MinJuz,
    "manzil.min.schema.json": MinManzil,
    "hizb.min.schema.json": MinHizb,
    "rub.min.schema.json": MinRub,
    "ruku.min.schema.json": MinRuku,
    "page.min.schema.json": MinPage,
    "sajdah.min.schema.json": MinSajdah,
    "scope-index.schema.json": ScopeIndex,
    "scope-index.min.schema.json": ScopeIndexMin,
    "index.schema.json": RootIndex,
    "index.min.schema.json": RootIndexMin,
    "quran.full.schema.json": QuranFull,
    "quran.full.min.schema.json": QuranFullMin,
}


def emit(target: Path) -> dict[str, Path]:
    target.mkdir(parents=True, exist_ok=True)
    written: dict[str, Path] = {}
    bundle: dict[str, Any] = {
        "$schema": _DIALECT,
        "$id": f"{_SCHEMA_BASE}/all.schema.json",
        "$comment": "quran-etl wire schema version 4",
        "title": "quran-etl public document bundle",
        "$defs": {},
        "oneOf": [],
    }
    for filename, model in _PUBLIC_MODELS.items():
        name = filename.removesuffix(".schema.json").replace(".", "-")
        schema = model.model_json_schema()
        schema["$schema"] = _DIALECT
        schema["$id"] = f"{_SCHEMA_BASE}/{filename}"
        schema["$comment"] = "quran-etl wire schema version 4"
        schema["title"] = name
        path = target / filename
        atomic_write_text(path, json.dumps(schema, ensure_ascii=False, indent=2))
        written[name] = path
        bundle["$defs"][name] = schema
        bundle["oneOf"].append({"$ref": f"#/$defs/{name}"})
    bundle_path = target / "all.schema.json"
    atomic_write_text(bundle_path, json.dumps(bundle, ensure_ascii=False, indent=2))
    written["all"] = bundle_path
    logger.info("wrote %d JSON Schemas to %s", len(written), target)
    return written
