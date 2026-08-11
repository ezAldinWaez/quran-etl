"""Unit tests for the transform stage."""

from __future__ import annotations

from quran_etl.transform import _expand_range, _expand_until_next, _prev_ayah


def test_prev_ayah_within_sura():
    assert _prev_ayah((2, 5)) == (2, 4)


def test_prev_ayah_at_sura_boundary():
    counts = [7, 286]
    assert _prev_ayah((2, 1), counts) == (1, 7)


def test_expand_range_within_sura():
    counts = [7, 286]  # sura 1 = 7, sura 2 = 286
    out = _expand_range((2, 1), (2, 5), counts)
    assert out == [(2, 1), (2, 2), (2, 3), (2, 4), (2, 5)]


def test_expand_range_crosses_sura():
    counts = [7, 286, 200]
    out = _expand_range((1, 5), (2, 3), counts)
    assert out == [(1, 5), (1, 6), (1, 7), (2, 1), (2, 2), (2, 3)]


def test_expand_until_next_basic():
    counts = [7, 286]
    out = _expand_until_next((1, 1), (2, 1), counts)
    assert out == [(1, 1), (1, 2), (1, 3), (1, 4), (1, 5), (1, 6), (1, 7)]


def test_expand_until_next_constrain_to_start_sura_crosses_zero():
    """If next_start is in a later surah, clip to end of starting surah."""
    counts = [7, 286]
    out = _expand_until_next((1, 1), (2, 1), counts, constrain_to_start_sura=True)
    assert out == [(1, 1), (1, 2), (1, 3), (1, 4), (1, 5), (1, 6), (1, 7)]


def test_expand_until_next_ruku_last_ayah_of_sura():
    """Mimic the ruku pattern: ruku starts at last ayah of a surah, next ruku in next surah."""
    counts = [3, 3]
    out = _expand_until_next((1, 3), (2, 1), counts, constrain_to_start_sura=True)
    assert out == [(1, 3)]


def test_expand_until_next_mid_sura_normal_case():
    counts = [10, 10, 10]
    out = _expand_until_next((1, 1), (1, 5), counts, constrain_to_start_sura=True)
    assert out == [(1, 1), (1, 2), (1, 3), (1, 4)]


def test_expand_until_next_degenerate_single_ayah():
    """A chunk that starts at the last ayah of a surah should still yield that one ayah."""
    counts = [3, 3]
    out = _expand_until_next((1, 3), (2, 1), counts, constrain_to_start_sura=True)
    assert out == [(1, 3)]
