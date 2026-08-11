"""Emit paired full and token-minimized Quran JSON files."""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .config import Settings
from .io_utils import atomic_write_text

logger = logging.getLogger(__name__)

SCHEMA_VERSION = 4
_MIN_SEPARATORS = (",", ":")
_AYAH_KEYS = {
    "key": "k",
    "text": "t",
    "text_clean": "tc",
    "sajda": "sj",
    "page": "p",
    "parents": "ps",
}
_AYAH_DROP = {
    "id",
    "sura",
    "aya",
    "global_id",
    "text_raw",
    "char_count",
    "word_count",
}
_SAJDA_CODES = {"obligatory": "o", "recommended": "r"}
_PARENT_CODES = {
    "surah": "s",
    "juz": "j",
    "manzil": "m",
    "ruku": "r",
    "hizb": "h",
    "rub": "q",
    "page": "p",
}
_SURAH_KEYS = {
    "id": "i",
    "key": "k",
    "name_arabic": "na",
    "name_transliteration": "nt",
    "name_english": "ne",
    "revelation_type": "rt",
    "ayah_count": "ac",
    "ruku_count": "rc",
    "start_ayah": "sa",
    "end_ayah": "ea",
    "ayahs": "a",
}
_SURAH_DROP = {
    "revelation_order",
    "bismillah_pretext",
    "ayah_ids",
    "parent_ids",
    "child_ids",
}
_RANGE_KEYS = {
    "id": "i",
    "key": "k",
    "start_ayah": "sa",
    "end_ayah": "ea",
    "ayah_count": "ac",
    "ayahs": "a",
}
_RANGE_DROP = {"ayah_ids", "parent_ids", "child_ids"}
_SCOPE_EXTRAS = {
    "juz": {"surahs_covered": "sc"},
    "manzil": {"surahs_covered": "sc"},
    "ruku": {"surah": "sh"},
    "hizb": {"juz_id": "ji"},
    "rub": {"hizb_id": "hi"},
}
_SCOPE_DROPS = {"ruku": {"surah_id"}}
_SAJDAH_KEYS = {
    "id": "i",
    "key": "k",
    "ayah": "ay",
    "type": "t",
    "surah": "sh",
    "ayah_data": "ad",
}
_SAJDAH_DROP = {"ayah_id", "surah_id", "parent_ids", "child_ids"}


def _write_full(path: Path, payload: Any, settings: Settings) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(
        payload,
        ensure_ascii=settings.ensure_ascii,
        indent=settings.indent,
        sort_keys=False,
    )
    atomic_write_text(path, text + "\n")


def _write_min(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, ensure_ascii=False, separators=_MIN_SEPARATORS)
    atomic_write_text(path, text)


def _minify_ayah_dict(obj: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in obj.items():
        if key in _AYAH_DROP:
            continue
        short = _AYAH_KEYS.get(key, key)
        if key == "parents" and isinstance(value, dict):
            out[short] = {
                _PARENT_CODES.get(scope, scope): parent
                for scope, parent in value.items()
            }
        elif key == "sajda" and isinstance(value, str):
            out[short] = _SAJDA_CODES.get(value, value)
        else:
            out[short] = value
    return out


def _minify_ayah(ayah: Any) -> dict[str, Any]:
    return _minify_ayah_dict(ayah.model_dump())


def _minify_surah(surah: Any) -> dict[str, Any]:
    payload = {
        key: value
        for key, value in surah.model_dump().items()
        if key not in _SURAH_DROP
    }
    out: dict[str, Any] = {}
    for key, value in payload.items():
        short = _SURAH_KEYS.get(key, key)
        if key == "ayahs" and isinstance(value, list):
            out[short] = [_minify_ayah_dict(ayah) for ayah in value]
        else:
            out[short] = value
    return out


def _minify_range_node(node: Any, scope: str) -> dict[str, Any]:
    extras = _SCOPE_EXTRAS.get(scope, {})
    drop = set(_RANGE_DROP) | set(extras) | _SCOPE_DROPS.get(scope, set())
    payload = {
        key: value for key, value in node.model_dump().items() if key not in drop
    }
    for full in extras:
        if hasattr(node, full):
            payload[full] = getattr(node, full)
    out: dict[str, Any] = {}
    for key, value in payload.items():
        short = extras.get(key, _RANGE_KEYS.get(key, key))
        if key == "ayahs" and isinstance(value, list):
            out[short] = [_minify_ayah_dict(ayah) for ayah in value]
        else:
            out[short] = value
    return out


def _minify_sajdah(sajdah: Any) -> dict[str, Any]:
    payload = {
        key: value
        for key, value in sajdah.model_dump().items()
        if key not in _SAJDAH_DROP
    }
    out: dict[str, Any] = {}
    for key, value in payload.items():
        short = _SAJDAH_KEYS.get(key, key)
        if key == "ayah_data" and isinstance(value, dict):
            out[short] = _minify_ayah_dict(value)
        elif key == "type" and isinstance(value, str):
            out[short] = _SAJDA_CODES.get(value, value)
        else:
            out[short] = value
    return out


def _scope_filename(scope: str, node: Any, *, minified: bool) -> str:
    digits = 3 if scope in {"surah", "ruku", "rub", "page"} else 2
    suffix = ".min.json" if minified else ".json"
    return f"{node.id:0{digits}d}{suffix}"


def _ayah_filename(ayah: Any, *, minified: bool) -> str:
    suffix = ".min.json" if minified else ".json"
    return f"{ayah.sura:03d}_{ayah.aya:03d}{suffix}"


def _emit_full(graph: dict[str, Any], settings: Settings) -> dict[str, Path]:
    data = settings.data_dir
    manifest: dict[str, Path] = {}
    surah_dir = data / "surah"
    surah_index: list[dict[str, Any]] = []
    for surah in graph["surahs"]:
        filename = _scope_filename("surah", surah, minified=False)
        surah_index.append(
            {
                "id": surah.id,
                "key": surah.key,
                "name_arabic": surah.name_arabic,
                "name_transliteration": surah.name_transliteration,
                "name_english": surah.name_english,
                "revelation_type": surah.revelation_type,
                "revelation_order": surah.revelation_order,
                "ayah_count": surah.ayah_count,
                "ruku_count": surah.ruku_count,
                "start": surah.start_ayah,
                "end": surah.end_ayah,
                "parents": surah.parent_ids,
                "children": {
                    "ayah_count": len(surah.child_ids.get("ayah", [])),
                    "ruku_count": len(surah.child_ids.get("ruku", [])),
                },
                "file": f"surah/{filename}",
            }
        )
        _write_full(surah_dir / filename, surah.model_dump(), settings)
    _write_full(surah_dir / "index.json", surah_index, settings)
    manifest["surah"] = surah_dir / "index.json"

    ayah_dir = data / "ayah"
    ayah_index: list[dict[str, Any]] = []
    for ayah in graph["ayahs"]:
        filename = _ayah_filename(ayah, minified=False)
        ayah_index.append(
            {
                "key": ayah.key,
                "id": ayah.id,
                "sura": ayah.sura,
                "aya": ayah.aya,
                "file": f"ayah/{filename}",
            }
        )
        _write_full(ayah_dir / filename, ayah.model_dump(), settings)
    _write_full(ayah_dir / "index.json", ayah_index, settings)
    manifest["ayah"] = ayah_dir / "index.json"

    scope_items = (
        ("juz", graph["juzs"]),
        ("manzil", graph["manzils"]),
        ("ruku", graph["rukus"]),
        ("hizb", graph["hizbs"]),
        ("rub", graph["rubs"]),
        ("page", graph["pages"]),
        ("sajdah", graph["sajdas"]),
    )
    for scope, items in scope_items:
        directory = data / scope
        index: list[dict[str, Any]] = []
        for node in items:
            filename = _scope_filename(scope, node, minified=False)
            entry: dict[str, Any] = {
                "id": node.id,
                "key": node.key,
                "file": f"{scope}/{filename}",
            }
            if scope == "sajdah":
                entry["ayah"] = node.ayah
                entry["type"] = node.type
            else:
                entry["start"] = node.start_ayah
                entry["end"] = node.end_ayah
                entry["ayah_count"] = node.ayah_count
            index.append(entry)
            _write_full(directory / filename, node.model_dump(), settings)
        _write_full(directory / "index.json", index, settings)
        manifest[scope] = directory / "index.json"

    generated_at = datetime.now(UTC).isoformat(timespec="seconds")
    full = {
        "meta": {
            "source": "tanzil.net",
            "text_type": settings.text_type,
            "ayat_count": len(graph["ayahs"]),
            "surah_count": len(graph["surahs"]),
            "juz_count": len(graph["juzs"]),
            "manzil_count": len(graph["manzils"]),
            "ruku_count": len(graph["rukus"]),
            "hizb_count": len(graph["hizbs"]),
            "rub_count": len(graph["rubs"]),
            "page_count": len(graph["pages"]),
            "sajdah_count": len(graph["sajdas"]),
            "generated_at": generated_at,
            "schema_version": SCHEMA_VERSION,
            "provenance": graph.get("provenance", {}),
        },
        "surahs": [surah.model_dump() for surah in graph["surahs"]],
        "juz": [node.model_dump() for node in graph["juzs"]],
        "manzil": [node.model_dump() for node in graph["manzils"]],
        "ruku": [node.model_dump() for node in graph["rukus"]],
        "hizb": [node.model_dump() for node in graph["hizbs"]],
        "rub": [node.model_dump() for node in graph["rubs"]],
        "pages": [node.model_dump() for node in graph["pages"]],
        "sajdah": [node.model_dump() for node in graph["sajdas"]],
    }
    full_path = data / "quran.full.json"
    _write_full(full_path, full, settings)
    manifest["quran.full"] = full_path
    root_index = {
        "version": SCHEMA_VERSION,
        "generated_at": generated_at,
        "scopes": {
            scope: str(path.relative_to(data)) for scope, path in manifest.items()
        },
        "totals": full["meta"],
    }
    root_path = data / "index.json"
    _write_full(root_path, root_index, settings)
    manifest["root"] = root_path
    return manifest


def _emit_minified(graph: dict[str, Any], settings: Settings) -> dict[str, Path]:
    data = settings.data_dir
    manifest: dict[str, Path] = {}
    scope_items = (
        ("surah", graph["surahs"], _minify_surah),
        ("juz", graph["juzs"], lambda node: _minify_range_node(node, "juz")),
        ("manzil", graph["manzils"], lambda node: _minify_range_node(node, "manzil")),
        ("ruku", graph["rukus"], lambda node: _minify_range_node(node, "ruku")),
        ("hizb", graph["hizbs"], lambda node: _minify_range_node(node, "hizb")),
        ("rub", graph["rubs"], lambda node: _minify_range_node(node, "rub")),
        ("page", graph["pages"], lambda node: _minify_range_node(node, "page")),
        ("sajdah", graph["sajdas"], _minify_sajdah),
    )
    for scope, items, minifier in scope_items:
        directory = data / scope
        index: list[dict[str, Any]] = []
        for node in items:
            filename = _scope_filename(scope, node, minified=True)
            _write_min(directory / filename, minifier(node))
            entry: dict[str, Any] = {
                "i": node.id,
                "k": node.key,
                "f": f"{scope}/{filename}",
            }
            if scope == "sajdah":
                entry["ay"] = node.ayah
                entry["t"] = _SAJDA_CODES.get(node.type, node.type)
            else:
                entry["sa"] = node.start_ayah
                entry["ea"] = node.end_ayah
                entry["ac"] = node.ayah_count
            index.append(entry)
        index_path = directory / "index.min.json"
        _write_min(index_path, index)
        manifest[scope] = index_path

    ayah_dir = data / "ayah"
    ayah_index: list[dict[str, Any]] = []
    for ayah in graph["ayahs"]:
        filename = _ayah_filename(ayah, minified=True)
        _write_min(ayah_dir / filename, _minify_ayah(ayah))
        ayah_index.append({"k": ayah.key, "f": f"ayah/{filename}"})
    ayah_index_path = ayah_dir / "index.min.json"
    _write_min(ayah_index_path, ayah_index)
    manifest["ayah"] = ayah_index_path

    generated_at = datetime.now(UTC).isoformat(timespec="seconds")
    full = {
        "m": {
            "src": "tanzil.net",
            "tt": settings.text_type,
            "ac": len(graph["ayahs"]),
            "sc": len(graph["surahs"]),
            "jc": len(graph["juzs"]),
            "mnc": len(graph["manzils"]),
            "rc": len(graph["rukus"]),
            "hc": len(graph["hizbs"]),
            "rbc": len(graph["rubs"]),
            "pc": len(graph["pages"]),
            "sac": len(graph["sajdas"]),
            "ga": generated_at,
            "sv": SCHEMA_VERSION,
            "sp": graph.get("provenance", {}),
        },
        "s": [_minify_surah(surah) for surah in graph["surahs"]],
        "j": [_minify_range_node(node, "juz") for node in graph["juzs"]],
        "mn": [_minify_range_node(node, "manzil") for node in graph["manzils"]],
        "rk": [_minify_range_node(node, "ruku") for node in graph["rukus"]],
        "hz": [_minify_range_node(node, "hizb") for node in graph["hizbs"]],
        "rb": [_minify_range_node(node, "rub") for node in graph["rubs"]],
        "pg": [_minify_range_node(node, "page") for node in graph["pages"]],
        "sj": [_minify_sajdah(sajdah) for sajdah in graph["sajdas"]],
    }
    full_path = data / "quran.full.min.json"
    _write_min(full_path, full)
    manifest["quran.full"] = full_path
    root_index = {
        "v": SCHEMA_VERSION,
        "ga": generated_at,
        "scopes": {
            scope: str(path.relative_to(data)) for scope, path in manifest.items()
        },
        "totals": full["m"],
    }
    root_path = data / "index.min.json"
    _write_min(root_path, root_index)
    manifest["root"] = root_path
    return manifest


def emit(
    graph: dict[str, Any],
    settings: Settings,
    *,
    include_full: bool = True,
    include_minified: bool = False,
) -> dict[str, dict[str, Path]]:
    """Write selected dataset variants and return their manifests."""
    if not include_full and not include_minified:
        raise ValueError("at least one dataset variant must be selected")
    manifests: dict[str, dict[str, Path]] = {}
    if include_full:
        manifests["full"] = _emit_full(graph, settings)
    if include_minified:
        manifests["minified"] = _emit_minified(graph, settings)
    logger.info("wrote paired dataset variants: %s", ", ".join(manifests))
    return manifests
