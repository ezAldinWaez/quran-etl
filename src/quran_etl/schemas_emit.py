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
    Page,
    Rub,
    Ruku,
    Sajdah,
    Surah,
)

logger = logging.getLogger(__name__)


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


def emit(target: Path) -> dict[str, Path]:
    target.mkdir(parents=True, exist_ok=True)
    written: dict[str, Path] = {}
    bundle: dict[str, Any] = {"$schema": "http://json-schema.org/draft-07/schema#",
                               "$id": "https://quran-etl.local/schemas/all.json",
                               "$comment": "quran-etl wire schema version 4",
                               "title": "quran-etl bundle",
                               "definitions": {}}
    for name, model in _MODELS.items():
        schema = model.model_json_schema()
        schema["$schema"] = "http://json-schema.org/draft-07/schema#"
        schema["$id"] = f"https://quran-etl.local/schemas/{name}.schema.json"
        schema["$comment"] = "quran-etl wire schema version 4"
        schema["title"] = name
        path = target / f"{name}.schema.json"
        atomic_write_text(path, json.dumps(schema, ensure_ascii=False, indent=2))
        written[name] = path
        bundle["definitions"][name] = schema
    bundle_path = target / "all.schema.json"
    atomic_write_text(bundle_path, json.dumps(bundle, ensure_ascii=False, indent=2))
    written["all"] = bundle_path
    logger.info("wrote %d JSON Schemas to %s", len(written), target)
    return written
