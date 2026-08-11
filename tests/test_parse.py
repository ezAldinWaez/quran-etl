"""Unit tests for the parsers."""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent

from quran_etl import parse


def test_parse_metadata_counts(tmp_path: Path):
    xml = dedent(
        """\
        <?xml version="1.0" encoding="utf-8"?>
        <quran>
          <suras>
            <sura index="1" ayas="7" start="0" name="x" tname="A" ename="B" type="Meccan" order="1" rukus="1"/>
            <sura index="2" ayas="2" start="7" name="y" tname="C" ename="D" type="Medinan" order="2" rukus="1"/>
          </suras>
          <juzs>
            <juz index="1" sura="1" aya="1"/>
            <juz index="2" sura="2" aya="2"/>
          </juzs>
          <hizbs>
            <hizb index="1"><quarter index="1" sura="1" aya="1"/></hizb>
            <hizb index="2"><quarter index="2" sura="1" aya="2"/></hizb>
            <hizb index="3"><quarter index="3" sura="1" aya="3"/></hizb>
            <hizb index="4"><quarter index="4" sura="2" aya="1"/></hizb>
          </hizbs>
          <manzils>
            <manzil index="1" sura="1" aya="1"/>
          </manzils>
          <rukus>
            <ruku index="1" sura="1" aya="1"/>
            <ruku index="2" sura="2" aya="1"/>
          </rukus>
          <pages>
            <page index="1" sura="1" aya="1"/>
          </pages>
          <sajdas>
            <sajda index="1" sura="1" aya="1" type="recommended"/>
          </sajdas>
        </quran>
        """
    )
    p = tmp_path / "m.xml"
    p.write_text(xml, encoding="utf-8")
    meta = parse.parse_metadata(p)
    assert len(meta["suras"]) == 2
    assert len(meta["juzs"]) == 2
    assert len(meta["quarters"]) == 4
    assert len(meta["hizbs"]) == 1  # we derived a single hizb of 4 quarters
    assert len(meta["manzils"]) == 1
    assert len(meta["rukus"]) == 2
    assert len(meta["pages"]) == 1
    assert len(meta["sajdas"]) == 1
    assert meta["sajdas"][0]["type"] == "recommended"


def test_parse_quran_text_basic(tmp_path: Path):
    content = "1|1|بسم\n1|2|الحمد\n2|1|الٓمٓ\n"
    p = tmp_path / "t.txt"
    p.write_text(content, encoding="utf-8")
    verses = parse.parse_quran_text(p)
    assert verses == {
        (1, 1): "بسم",
        (1, 2): "الحمد",
        (2, 1): "الٓمٓ",
    }


def test_parse_quran_text_skips_comments(tmp_path: Path):
    content = "# header comment\n1|1|بسم\n"
    p = tmp_path / "t.txt"
    p.write_text(content, encoding="utf-8")
    verses = parse.parse_quran_text(p)
    assert verses == {(1, 1): "بسم"}


def test_parse_quran_text_malformed(tmp_path: Path):
    p = tmp_path / "t.txt"
    p.write_text("not a verse line\n", encoding="utf-8")
    import pytest
    with pytest.raises(ValueError):
        parse.parse_quran_text(p)
