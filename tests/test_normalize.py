"""Unit tests for the Arabic normalizer."""

from __future__ import annotations

from quran_etl import normalize


def test_nfc_normalization():
    # The normalizer should be a no-op for NFC strings and fold NFD to NFC.
    import unicodedata
    raw = "بِسْمِ"
    decomposed = unicodedata.normalize("NFD", raw)
    assert normalize.normalize_arabic(raw) == raw
    assert normalize.normalize_arabic(decomposed) == raw


def test_strip_bismillah_basic():
    text = "بِسْمِ ٱللَّهِ ٱلرَّحْمَٰنِ ٱلرَّحِيمِ ٱلْحَمْدُ لِلَّهِ رَبِّ ٱلْعَـٰلَمِينَ"
    stripped = normalize.strip_bismillah(text)
    assert "ٱلْحَمْدُ" in stripped
    assert "بِسْمِ" not in stripped


def test_strip_bismillah_does_not_remove_non_bismillah():
    text = "لَمْ يَكُنِ ٱلَّذِينَ كَفَرُوا"
    assert normalize.strip_bismillah(text) == text


def test_strip_bismillah_handles_tanzil_combining_mark_variants():
    regular = "بِسْمِ ٱللَّهِ ٱلرَّحْمَٰنِ ٱلرَّحِيمِ الٓمٓ"
    doubled = "بِّسْمِ ٱللَّهِ ٱلرَّحْمَٰنِ ٱلرَّحِيمِ وَٱلتِّينِ"
    assert normalize.strip_bismillah(regular) == "الٓمٓ"
    assert normalize.strip_bismillah(doubled) == "وَٱلتِّينِ"


def test_strip_marks_removes_sajdah_and_rub():
    text = "قَالَ ٱللَّهُ ۩ لَا۞ إِلَـٰهَ"
    out = normalize.strip_marks(text)
    assert "۩" not in out
    assert "۞" not in out
    assert "قَالَ ٱللَّهُ" in out
    assert "لَا" in out


def test_remove_diacritics():
    text = "بِسْمِ ٱللَّهِ"
    out = normalize.remove_diacritics(text)
    # No combining diacritics remain
    assert "\u0650" not in out
    assert "\u064E" not in out
    assert "\u0651" not in out
    assert "بسم" in out


def test_search_text_strips_marks_and_diacritics():
    text = "بِسْمِ ٱللَّهِ ٱلرَّحْمَٰنِ ٱلرَّحِيمِ ۞"
    s = normalize.search_text(text)
    # Basic diacritics removal
    assert "بسم" in s
    # Marks removed
    assert "۞" not in s
    # All combining diacritics removed
    for d in ("\u064E", "\u064F", "\u0650", "\u0651", "\u0652", "\u0670"):
        assert d not in s
    # The leading alef wasla (ٱ) survives because it is a letter, not a
    # combining mark — that's intentional, since it affects pronunciation
    # and is meaningful for exact search.
    assert "ٱل" in s


def test_word_count():
    assert normalize.word_count("بِسْمِ ٱللَّهِ ٱلرَّحْمَٰنِ ٱلرَّحِيمِ") == 4
    assert normalize.word_count("") == 0
    # tatweel is in-word glue; a token with tatweel still counts as one word
    assert normalize.word_count("ٱلرَّحْمَـٰن") >= 1


def test_char_count_uses_codepoints():
    assert normalize.char_count("بسم") == 3
