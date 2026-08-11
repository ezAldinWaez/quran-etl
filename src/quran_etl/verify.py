from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .config import Settings
from .normalize import strip_bismillah, strip_marks

EXPECTED_COUNTS = {
    "surah": 114,
    "ayah": 6236,
    "juz": 30,
    "manzil": 7,
    "ruku": 556,
    "hizb": 60,
    "rub": 240,
    "page": 604,
    "sajdah": 15,
}
RANGE_SCOPES = ("surah", "juz", "manzil", "ruku", "hizb", "rub", "page")
PARENT_SCOPES = ("juz", "manzil", "ruku", "hizb", "rub", "page")
PARENT_CODES = {"surah": "s", "juz": "j", "manzil": "m", "ruku": "r", "hizb": "h", "rub": "q", "page": "p"}


def _read(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_indexed(
    root: Path, scope: str, file_key: str, index_name: str = "index.json"
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    index_path = root / scope / index_name
    index = _read(index_path)
    return index, [_read(root / entry[file_key]) for entry in index]


def _check_files(
    root: Path,
    scope: str,
    index: list[dict[str, Any]],
    file_key: str,
    errors: list[str],
    *,
    minified: bool = False,
) -> None:
    expected = {"index.min.json" if minified else "index.json"}
    expected.update(Path(entry[file_key]).name for entry in index)
    actual = {
        path.name
        for path in (root / scope).glob("*.json")
        if path.name.endswith(".min.json") == minified
    }
    if actual != expected:
        errors.append(
            f"{scope} JSON file set mismatch: missing={sorted(expected - actual)[:5]}, "
            f"unexpected={sorted(actual - expected)[:5]}"
        )


def _membership(
    nodes: list[dict[str, Any]],
    ayah_field: str,
    key_field: str,
    scope: str,
    all_ayahs: set[str],
    errors: list[str],
) -> dict[str, str]:
    result: dict[str, str] = {}
    for node in nodes:
        node_key = node.get(key_field, f"unknown-{scope}")
        values = node.get(ayah_field)
        if not isinstance(values, list):
            errors.append(f"{node_key} is missing list field {ayah_field}")
            continue
        ayah_keys = [value["k"] for value in values] if values and isinstance(values[0], dict) else values
        for ayah_key in ayah_keys:
            if ayah_key in result:
                errors.append(f"{scope} duplicates ayah {ayah_key}")
            result[ayah_key] = node_key
    if set(result) != all_ayahs:
        errors.append(
            f"{scope} coverage mismatch: missing={len(all_ayahs - set(result))}, "
            f"extra={len(set(result) - all_ayahs)}"
        )
    return result


def _expected_text(text_raw: str, sura: int, aya: int, settings: Settings) -> str:
    value = strip_marks(text_raw)
    if (
        settings.strip_bismillah_from_non_fatiha
        and aya == 1
        and sura not in set(settings.bismillah_exempt_surahs)
    ):
        value = strip_bismillah(value)
    return value.strip()


def verify_full(
    root: Path,
    settings: Settings,
    expected_counts: dict[str, int] | None = None,
) -> list[str]:
    errors: list[str] = []
    counts = expected_counts or EXPECTED_COUNTS
    indexes: dict[str, list[dict[str, Any]]] = {}
    nodes: dict[str, list[dict[str, Any]]] = {}
    try:
        for scope in counts:
            indexes[scope], nodes[scope] = _load_indexed(root, scope, "file")
            if len(indexes[scope]) != counts[scope]:
                errors.append(
                    f"{scope} index has {len(indexes[scope])} entries, expected {counts[scope]}"
                )
            _check_files(root, scope, indexes[scope], "file", errors)
    except (OSError, KeyError, TypeError, json.JSONDecodeError) as exc:
        return [f"cannot read full dataset: {exc}"]
    root_files = {
        path.name
        for path in root.glob("*.json")
        if not path.name.endswith(".min.json")
    }
    expected_root_files = {"index.json", "quran.full.json"}
    if root_files != expected_root_files:
        errors.append(
            f"root JSON file set mismatch: missing={sorted(expected_root_files - root_files)}, "
            f"unexpected={sorted(root_files - expected_root_files)}"
        )

    ayahs = {ayah["key"]: ayah for ayah in nodes["ayah"]}
    all_ayahs = set(ayahs)
    if len(ayahs) != counts["ayah"]:
        errors.append(f"ayah keys are not unique: {len(ayahs)} unique")

    memberships: dict[str, dict[str, str]] = {}
    for scope in RANGE_SCOPES:
        for node in nodes[scope]:
            inline = node.get("ayahs")
            ayah_ids = node.get("ayah_ids")
            if not isinstance(inline, list) or not isinstance(ayah_ids, list):
                errors.append(f"{node.get('key', scope)} is missing inline ayahs or ayah_ids")
                continue
            inline_keys = [ayah["key"] for ayah in inline]
            if inline_keys != ayah_ids:
                errors.append(f"{node['key']} inline ayahs do not match ayah_ids")
            if node["ayah_count"] != len(ayah_ids):
                errors.append(f"{node['key']} ayah_count is incorrect")
            if ayah_ids and (node["start_ayah"] != ayah_ids[0] or node["end_ayah"] != ayah_ids[-1]):
                errors.append(f"{node['key']} range endpoints are incorrect")
            expected_children = [f"ayah:{key}" for key in ayah_ids]
            if node.get("child_ids", {}).get("ayah") != expected_children:
                errors.append(f"{node['key']} ayah child IDs are incorrect")
        memberships[scope] = _membership(
            nodes[scope], "ayah_ids", "key", scope, all_ayahs, errors
        )

    for key, ayah in ayahs.items():
        expected_parents = {"surah": memberships["surah"].get(key, "")}
        expected_parents.update({scope: memberships[scope].get(key, "") for scope in PARENT_SCOPES})
        if ayah.get("parents") != expected_parents:
            errors.append(f"ayah {key} parent map is incorrect")
        page_key = memberships["page"].get(key, "page:000")
        if ayah.get("page") != int(page_key.split(":")[1]):
            errors.append(f"ayah {key} page scalar is incorrect")
        if ayah.get("text") != _expected_text(ayah["text_raw"], ayah["sura"], ayah["aya"], settings):
            errors.append(f"ayah {key} normalized text is incorrect")
        if (
            settings.strip_bismillah_from_non_fatiha
            and ayah["aya"] == 1
            and ayah["sura"] not in set(settings.bismillah_exempt_surahs)
        ):
            raw_without_marks = strip_marks(ayah["text_raw"])
            if strip_bismillah(raw_without_marks) == raw_without_marks.strip():
                errors.append(f"ayah {key} raw text lacks its configured Bismillah prefix")
            if strip_bismillah(ayah["text"]) != ayah["text"]:
                errors.append(f"ayah {key} still contains a Bismillah prefix")

    for surah in nodes["surah"]:
        for scope in PARENT_SCOPES:
            expected = list(dict.fromkeys(memberships[scope][key] for key in surah["ayah_ids"]))
            if surah["child_ids"].get(scope) != expected:
                errors.append(f"{surah['key']} {scope} children are incorrect")
        if surah.get("parent_ids") != []:
            errors.append(f"{surah['key']} must not have parents")

    for scope in ("juz", "manzil", "page"):
        for node in nodes[scope]:
            if node.get("parent_ids") != []:
                errors.append(f"{node['key']} must not have synthetic parents")

    for node in nodes["ruku"]:
        expected = memberships["surah"][node["start_ayah"]]
        if node.get("parent_ids") != [expected] or node.get("surah_id") != expected:
            errors.append(f"{node['key']} surah relationship is incorrect")

    for node in nodes["juz"]:
        expected = list(dict.fromkeys(memberships["hizb"][key] for key in node["ayah_ids"]))
        if node["child_ids"].get("hizb") != expected:
            errors.append(f"{node['key']} hizb children are incorrect")

    for node in nodes["hizb"]:
        parent = memberships["juz"][node["start_ayah"]]
        expected_rubs = list(dict.fromkeys(memberships["rub"][key] for key in node["ayah_ids"]))
        if node.get("juz_id") != parent or node.get("parent_ids") != [parent]:
            errors.append(f"{node['key']} juz relationship is incorrect")
        if node["child_ids"].get("rub") != expected_rubs:
            errors.append(f"{node['key']} rub children are incorrect")

    for node in nodes["rub"]:
        hizb = memberships["hizb"][node["start_ayah"]]
        juz = memberships["juz"][node["start_ayah"]]
        if node.get("hizb_id") != hizb or node.get("parent_ids") != [hizb, juz]:
            errors.append(f"{node['key']} parent relationship is incorrect")

    for node in nodes["sajdah"]:
        ayah_key = node.get("ayah")
        if ayah_key not in ayahs or node.get("ayah_data", {}).get("key") != ayah_key:
            errors.append(f"{node.get('key', 'sajdah')} references an invalid ayah")
        expected_surah = memberships["surah"].get(ayah_key, "")
        if node.get("parent_ids") != [expected_surah]:
            errors.append(f"{node['key']} surah parent is incorrect")

    try:
        full = _read(root / "quran.full.json")
        meta = full.get("meta", {})
        if meta.get("schema_version") != 4:
            errors.append("quran.full.json is not schema version 4")
        if not meta.get("provenance"):
            errors.append("quran.full.json is missing source provenance")
        if len(full.get("surahs", [])) != counts["surah"]:
            errors.append("quran.full.json has incorrect surah count")
        manifest = _read(root / "index.json")
        if manifest.get("version") != 4:
            errors.append("full index.json is not version 4")
    except (OSError, TypeError, json.JSONDecodeError) as exc:
        errors.append(f"cannot read quran.full.json: {exc}")
    return errors


def verify_min(
    root: Path,
    settings: Settings,
    expected_counts: dict[str, int] | None = None,
) -> list[str]:
    errors: list[str] = []
    counts = expected_counts or EXPECTED_COUNTS
    indexes: dict[str, list[dict[str, Any]]] = {}
    nodes: dict[str, list[dict[str, Any]]] = {}
    try:
        for scope in counts:
            indexes[scope], nodes[scope] = _load_indexed(
                root, scope, "f", "index.min.json"
            )
            if len(indexes[scope]) != counts[scope]:
                errors.append(
                    f"{scope} min index has {len(indexes[scope])} entries, expected {counts[scope]}"
                )
            _check_files(
                root, scope, indexes[scope], "f", errors, minified=True
            )
    except (OSError, KeyError, TypeError, json.JSONDecodeError) as exc:
        return [f"cannot read minified dataset: {exc}"]
    root_files = {
        path.name
        for path in root.glob("*.json")
        if path.name.endswith(".min.json")
    }
    expected_root_files = {"index.min.json", "quran.full.min.json"}
    if root_files != expected_root_files:
        errors.append(
            f"min root JSON file set mismatch: missing={sorted(expected_root_files - root_files)}, "
            f"unexpected={sorted(root_files - expected_root_files)}"
        )

    ayahs = {ayah["k"]: ayah for ayah in nodes["ayah"]}
    all_ayahs = set(ayahs)
    memberships: dict[str, dict[str, str]] = {}
    for scope in RANGE_SCOPES:
        if scope == "surah":
            allowed = {"i", "k", "na", "nt", "ne", "rt", "ac", "rc", "sa", "ea", "a"}
        else:
            allowed = {"i", "k", "sa", "ea", "ac", "a"}
            allowed.update({"juz": {"sc"}, "manzil": {"sc"}, "ruku": {"sh"}, "hizb": {"ji"}, "rub": {"hi"}}.get(scope, set()))
        for node in nodes[scope]:
            if set(node) != allowed:
                errors.append(f"{node.get('k', scope)} has invalid short keys")
            inline_keys = [ayah["k"] for ayah in node.get("a", [])]
            if node.get("ac") != len(inline_keys):
                errors.append(f"{node.get('k', scope)} min ayah_count is incorrect")
            if inline_keys and (node.get("sa") != inline_keys[0] or node.get("ea") != inline_keys[-1]):
                errors.append(f"{node.get('k', scope)} min endpoints are incorrect")
        memberships[scope] = _membership(nodes[scope], "a", "k", scope, all_ayahs, errors)

    ayah_keys = {"k", "t", "tc", "sj", "p", "ps"}
    for key, ayah in ayahs.items():
        if set(ayah) != ayah_keys:
            errors.append(f"ayah {key} has invalid short keys")
        expected = {"s": memberships["surah"].get(key, "")}
        expected.update({PARENT_CODES[scope]: memberships[scope].get(key, "") for scope in PARENT_SCOPES})
        if ayah.get("ps") != expected:
            errors.append(f"ayah {key} min parent map is incorrect")
        page_key = memberships["page"].get(key, "page:000")
        if ayah.get("p") != int(page_key.split(":")[1]):
            errors.append(f"ayah {key} min page scalar is incorrect")
        if key.split(":")[1] == "1" and int(key.split(":")[0]) not in set(settings.bismillah_exempt_surahs):
            if strip_bismillah(ayah.get("t", "")) != ayah.get("t", ""):
                errors.append(f"ayah {key} still contains a Bismillah prefix")

    for node in nodes["sajdah"]:
        if set(node) != {"i", "k", "ay", "t", "sh", "ad"}:
            errors.append(f"{node.get('k', 'sajdah')} has invalid short keys")
        ayah_key = node.get("ay")
        if ayah_key not in ayahs or node.get("ad", {}).get("k") != ayah_key:
            errors.append(f"{node.get('k', 'sajdah')} references an invalid min ayah")

    try:
        full = _read(root / "quran.full.min.json")
        meta = full.get("m", {})
        if meta.get("sv") != 4:
            errors.append("quran.full.min.json is not schema version 4")
        if not meta.get("sp"):
            errors.append("quran.full.min.json is missing source provenance")
        if len(full.get("s", [])) != counts["surah"]:
            errors.append("quran.full.min.json has incorrect surah count")
        manifest = _read(root / "index.min.json")
        if manifest.get("v") != 4:
            errors.append("min index.min.json is not version 4")
    except (OSError, TypeError, json.JSONDecodeError) as exc:
        errors.append(f"cannot read quran.full.min.json: {exc}")
    return errors
