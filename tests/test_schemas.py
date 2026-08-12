from __future__ import annotations

import json
from pathlib import Path

from jsonschema.validators import validator_for

from quran_etl.schemas_emit import emit

from .support import emit_twelve_surah_datasets


def _read(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _validate(payload_path: Path, schema_path: Path) -> None:
    schema = _read(schema_path)
    validator = validator_for(schema)
    validator.check_schema(schema)
    validator(schema).validate(_read(payload_path))


def test_committed_public_schemas_are_current(tmp_path: Path):
    generated = tmp_path / "schemas"
    emit(generated)
    committed = Path("docs/json-schema")
    assert {path.name for path in generated.glob("*.json")} == {
        path.name for path in committed.glob("*.json")
    }
    for path in generated.glob("*.json"):
        assert _read(path) == _read(committed / path.name)


def test_all_emitted_document_kinds_validate_against_public_schemas(tmp_path: Path):
    settings, _ = emit_twelve_surah_datasets(tmp_path)
    schemas = Path("docs/json-schema")
    scopes = ("ayah", "surah", "juz", "manzil", "hizb", "rub", "ruku", "page", "sajdah")
    filenames = {
        "ayah": "001_001",
        "surah": "001",
        "juz": "01",
        "manzil": "01",
        "hizb": "01",
        "rub": "001",
        "ruku": "001",
        "page": "001",
        "sajdah": "01",
    }
    for scope in scopes:
        base = settings.data_dir / scope / filenames[scope]
        _validate(base.with_suffix(".json"), schemas / f"{scope}.schema.json")
        _validate(base.with_suffix(".min.json"), schemas / f"{scope}.min.schema.json")
        _validate(settings.data_dir / scope / "index.json", schemas / "scope-index.schema.json")
        _validate(
            settings.data_dir / scope / "index.min.json",
            schemas / "scope-index.min.schema.json",
        )
    _validate(settings.data_dir / "quran.full.json", schemas / "quran.full.schema.json")
    _validate(settings.data_dir / "quran.full.min.json", schemas / "quran.full.min.schema.json")
    _validate(settings.data_dir / "index.json", schemas / "index.schema.json")
    _validate(settings.data_dir / "index.min.json", schemas / "index.min.schema.json")
    _validate(settings.data_dir / "ayah" / "001_001.json", schemas / "all.schema.json")
    _validate(settings.data_dir / "ayah" / "001_001.min.json", schemas / "all.schema.json")
    _validate(settings.data_dir / "ayah" / "index.json", schemas / "all.schema.json")
    _validate(settings.data_dir / "index.json", schemas / "all.schema.json")


def test_public_schemas_require_denormalized_fields_and_bundle_has_a_root():
    schemas = Path("docs/json-schema")
    surah_schema = _read(schemas / "surah.schema.json")
    assert {"child_ids", "ayahs"} <= set(surah_schema["required"])
    ayah_schema = _read(schemas / "ayah.schema.json")
    assert "sajda" in ayah_schema["required"]
    bundle = _read(schemas / "all.schema.json")
    validator = validator_for(bundle)
    validator.check_schema(bundle)
    assert not validator(bundle).is_valid(42)
