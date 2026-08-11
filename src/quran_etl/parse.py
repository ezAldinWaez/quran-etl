"""Parsers for Tanzil.net sources.

- `parse_metadata`: quran-data.xml -> typed dicts
- `parse_quran_text`: quran-uthmani.txt -> dict[(sura,aya)] -> text
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

logger = logging.getLogger(__name__)


def _xml_text(path: Path, *, encoding: str = "utf-8") -> ET.Element:
    """Read XML safely. Try multiple encodings if the default fails."""
    raw = path.read_bytes()
    # Common Tanzil XML is saved as cp1256 / windows-1256 in some mirrors;
    # the canonical tanzil.net file is UTF-8 in spirit but historically used
    # cp1256 for the Arabic sura names. Try cp1256 first as a fallback.
    for enc in (encoding, "cp1256", "windows-1256", "utf-8-sig", "latin-1"):
        try:
            text = raw.decode(enc)
            return ET.fromstring(text)
        except (UnicodeDecodeError, ET.ParseError):
            continue
    raise RuntimeError(f"could not parse XML {path} with any tried encoding")


def parse_metadata(path: Path) -> dict[str, Any]:
    """Parse quran-data.xml into a dict of lists.

    Notes on Tanzil's structure:
    - <suras>, <juzs>, <manzils>, <rukus>, <pages>, <sajdas> each contain
      flat lists of their items.
    - <hizbs> contains only <quarter> children (240 of them). The hizb
      boundaries (60 of them) are not given directly and must be derived
      as the start ayah of every 4th quarter.
    """
    root = _xml_text(path)
    out: dict[str, Any] = {"suras": [], "juzs": [], "hizbs": [], "quarters": [],
                            "manzils": [], "rukus": [], "pages": [], "sajdas": []}
    for child in root:
        tag = child.tag
        if tag == "suras":
            out["suras"] = [_attribs(s) for s in child.findall("sura")]
        elif tag in ("juzs",):
            out["juzs"] = [_attribs(j) for j in child.findall("juz")]
        elif tag in ("hizbs",):
            out["quarters"] = [_attribs(q) for q in child.findall(".//quarter")]
        elif tag in ("quarters",):
            out["quarters"] = [_attribs(q) for q in child.findall("quarter")]
        elif tag in ("manzils",):
            out["manzils"] = [_attribs(m) for m in child.findall("manzil")]
        elif tag in ("rukus",):
            out["rukus"] = [_attribs(r) for r in child.findall("ruku")]
        elif tag in ("pages",):
            out["pages"] = [_attribs(p) for p in child.findall("page")]
        elif tag in ("sajdas",):
            out["sajdas"] = [_attribs(s) for s in child.findall("sajda")]

    # Derive hizbs: hizb k starts at the same ayah as quarter (4k - 3)
    # and contains quarters (4k-3) .. (4k).
    quarters = out["quarters"]
    if len(quarters) % 4 != 0:
        raise ValueError(f"expected 240 quarters, got {len(quarters)}")
    derived_hizbs: list[dict[str, str]] = []
    for hizb_idx in range(len(quarters) // 4):
        q = quarters[hizb_idx * 4]
        derived_hizbs.append({
            "index": str(hizb_idx + 1),
            "sura": q["sura"],
            "aya": q["aya"],
        })
    out["hizbs"] = derived_hizbs
    logger.info(
        "metadata: %d suras, %d juz, %d hizb (derived), %d quarters, %d manzils, %d rukus, %d pages, %d sajdas",
        len(out["suras"]), len(out["juzs"]), len(out["hizbs"]),
        len(out["quarters"]), len(out["manzils"]), len(out["rukus"]),
        len(out["pages"]), len(out["sajdas"]),
    )
    return out


def _attribs(el: ET.Element) -> dict[str, str]:
    return {k: v for k, v in el.attrib.items()}


# Quran text formats:
#   "sura|aya|text"          (quran-uthmani.txt with aya numbers)
#   "sura|aya|text\n"        (same, line-terminated)
_TEXT_LINE_RE = re.compile(r"^(\d+)\|(\d+)\|(.*)$")


def parse_quran_text(path: Path) -> dict[tuple[int, int], str]:
    """Parse quran-uthmani.txt (or any Tanzil text-with-aya-numbers file)."""
    verses: dict[tuple[int, int], str] = {}
    with path.open("r", encoding="utf-8", newline="") as f:
        for lineno, raw in enumerate(f, 1):
            line = raw.rstrip("\r\n")
            if not line:
                continue
            m = _TEXT_LINE_RE.match(line)
            if not m:
                # Some Tanzil files include a 1-line header like "# Format: ..."
                # — skip lines that clearly aren't verse records.
                if line.lstrip().startswith("#"):
                    continue
                raise ValueError(f"malformed line at {path}:{lineno}: {line!r}")
            sura, aya, text = int(m.group(1)), int(m.group(2)), m.group(3)
            verses[(sura, aya)] = text
    logger.info("quran text: %d verses parsed from %s", len(verses), path.name)
    return verses
