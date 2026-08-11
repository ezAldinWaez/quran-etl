"""Arabic-text normalization."""

from __future__ import annotations

import re
import unicodedata

# Diacritics: combining marks U+0610..U+061A, U+064B..U+065F, U+0670, U+06D6..U+06DC, U+06DF..U+06E4,
# U+06E7..U+06E8, U+06EA..U+06ED, U+08D3..U+08E1, U+08E3..U+08FF
_DIACRITICS_RE = re.compile(r"[\u0610-\u061A\u064B-\u065F\u0670\u06D6-\u06DC\u06DF-\u06E4"
                            r"\u06E7\u06E8\u06EA-\u06ED\u08D3-\u08E1\u08E3-\u08FF]")

# Tatweel
_TATWEEL = "\u0640"

_ARABIC_MARKS = (
    "\u0610-\u061A\u064B-\u065F\u0670\u06D6-\u06DC\u06DF-\u06E4"
    "\u06E7\u06E8\u06EA-\u06ED\u08D3-\u08E1\u08E3-\u08FF"
)
_MARKS = f"[{_ARABIC_MARKS}]*"


def _marked_word(letters: str) -> str:
    return "".join(f"{re.escape(letter)}{_MARKS}" for letter in letters)


def _marked_article_word(letters: str) -> str:
    return f"[ٱا]{_MARKS}{_marked_word(letters)}"


_BISMILLAH_RE = re.compile(
    rf"^\s*{_marked_word('بسم')}\s+"
    rf"{_marked_article_word('لله')}\s+"
    rf"{_marked_article_word('لرحمن')}\s+"
    rf"{_marked_article_word('لرحيم')}(?:\s+|$)"
)

_SAJDAH_MARK = "\u06E9"  # ۩ Arabic end of ayah (sajdah sign)
_RUB_MARK = "\u06DE"  # ۞ Arabic start of rub el hizb

def normalize_arabic(text: str, form: str = "NFC") -> str:
    """Unicode-normalize Arabic text (default NFC)."""
    return unicodedata.normalize(form, text)


def strip_bismillah(text: str) -> str:
    """Remove a leading Bismillah from a verse, if present.

    The first ayah of every surah (except Al-Fatiha and At-Tawba in the
    standard Uthmani text) opens with the Bismillah. Tanzil's `quran-uthmani.txt`
    includes the Bismillah as part of the first ayah's text, so we strip it
    so the first ayah reads as the actual verse.
    """
    normalized = normalize_arabic(text)
    return _BISMILLAH_RE.sub("", normalized, count=1).strip()


def strip_marks(text: str, *, keep_rub: bool = False) -> str:
    """Remove the sajdah and optional rub symbols embedded by Tanzil."""
    chars = list(text)
    out: list[str] = []
    for c in chars:
        if c == _SAJDAH_MARK:
            continue
        if c == _RUB_MARK and not keep_rub:
            continue
        out.append(c)
    return "".join(out)


def remove_diacritics(text: str) -> str:
    return _DIACRITICS_RE.sub("", text)


def search_text(text: str) -> str:
    """A diacritics-free, mark-free version suitable for substring search."""
    s = strip_marks(text, keep_rub=False)
    s = remove_diacritics(s)
    return s


def word_count(text: str) -> int:
    """Whitespace-based word count, with tatweel treated as in-word glue."""
    cleaned = text.replace(_TATWEEL, "")
    tokens = [t for t in re.split(r"\s+", cleaned.strip()) if t]
    return len(tokens)


def char_count(text: str) -> int:
    return len(text)
