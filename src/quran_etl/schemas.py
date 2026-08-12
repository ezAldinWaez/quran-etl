"""Pydantic models for the entire Quran data graph.

Every node carries stable `id` + `key` and full parent/child cross-references,
and the actual Quran text is **denormalized** inline so each per-scope
file is fully self-contained for analytics — no joins, no lookups.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, RootModel


class WireModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


AyahKey = str
SajdaType = Literal["obligatory", "recommended"]
MinSajdaType = Literal["o", "r"]


class MinAyahParents(WireModel):
    s: str
    j: str
    m: str
    r: str
    h: str
    q: str
    p: str

# ---------- Leaf: Ayah -----------------------------------------------------


class Ayah(WireModel):
    """A single Quranic verse — the leaf of the tree."""

    key: AyahKey = Field(pattern=r"^[1-9][0-9]{0,2}:[1-9][0-9]{0,2}$")
    id: str = Field(pattern=r"^ayah:[1-9][0-9]{0,2}:[1-9][0-9]{0,2}$")
    global_id: int = Field(ge=1, le=6236)
    sura: int = Field(ge=1, le=114)
    aya: int = Field(ge=1)
    text: str  # normalized Uthmani (or whatever text-type)
    text_raw: str  # exactly as Tanzil delivered it
    text_clean: str  # search-friendly, no diacritics
    char_count: int = Field(ge=0)
    word_count: int = Field(ge=0)
    sajda: SajdaType | None
    page: int = Field(ge=1, le=604)
    parents: dict[str, str]


# ---------- Surah ---------------------------------------------------------


class Surah(WireModel):
    id: int = Field(ge=1, le=114)
    key: str = Field(pattern=r"^surah:[0-9]{3}$")
    name_arabic: str
    name_transliteration: str
    name_english: str
    revelation_type: Literal["Meccan", "Medinan"]
    revelation_order: int = Field(ge=1, le=114)
    ayah_count: int = Field(ge=1)
    ruku_count: int = Field(ge=0)
    bismillah_pretext: bool
    start_ayah: str
    end_ayah: str
    ayah_ids: list[str]
    parent_ids: list[str]
    child_ids: dict[str, list[str]]
    ayahs: list[Ayah]


# ---------- Juz -----------------------------------------------------------


class Juz(WireModel):
    id: int = Field(ge=1, le=30)
    key: str = Field(pattern=r"^juz:[0-9]{2}$")
    start_ayah: str
    end_ayah: str
    ayah_count: int = Field(ge=1)
    ayah_ids: list[str]
    parent_ids: list[str]
    child_ids: dict[str, list[str]]
    surahs_covered: list[str]
    ayahs: list[Ayah]


# ---------- Manzil --------------------------------------------------------


class Manzil(WireModel):
    id: int = Field(ge=1, le=7)
    key: str = Field(pattern=r"^manzil:[0-9]{2}$")
    start_ayah: str
    end_ayah: str
    ayah_count: int = Field(ge=1)
    ayah_ids: list[str]
    parent_ids: list[str]
    child_ids: dict[str, list[str]]
    surahs_covered: list[str]
    ayahs: list[Ayah]


# ---------- Sajdah -------------------------------------------------------


class Sajdah(WireModel):
    id: int = Field(ge=1, le=15)
    key: str = Field(pattern=r"^sajdah:[0-9]{2}$")
    ayah: str  # e.g. "22:18"
    ayah_id: str
    type: SajdaType
    surah: str
    surah_id: str
    parent_ids: list[str]
    child_ids: dict[str, list[str]]
    # denormalized: the single ayah it points to (full object)
    ayah_data: Ayah


# ---------- Ruku ----------------------------------------------------------


class Ruku(WireModel):
    id: int = Field(ge=1, le=556)
    key: str = Field(pattern=r"^ruku:[0-9]{3}$")
    start_ayah: str
    end_ayah: str
    ayah_count: int = Field(ge=1)
    ayah_ids: list[str]
    parent_ids: list[str]
    child_ids: dict[str, list[str]]
    surah: str
    surah_id: str
    ayahs: list[Ayah]


# ---------- Hizb ---------------------------------------------------------


class Hizb(WireModel):
    id: int = Field(ge=1, le=60)
    key: str = Field(pattern=r"^hizb:[0-9]{2}$")
    start_ayah: str
    end_ayah: str
    ayah_count: int = Field(ge=1)
    ayah_ids: list[str]
    parent_ids: list[str]
    child_ids: dict[str, list[str]]
    juz_id: str
    ayahs: list[Ayah]


# ---------- Rub (Hizb quarter) -------------------------------------------


class Rub(WireModel):
    id: int = Field(ge=1, le=240)
    key: str = Field(pattern=r"^rub:[0-9]{3}$")
    start_ayah: str
    end_ayah: str
    ayah_count: int = Field(ge=1)
    ayah_ids: list[str]
    parent_ids: list[str]
    child_ids: dict[str, list[str]]
    hizb_id: str
    ayahs: list[Ayah]


# ---------- Page ---------------------------------------------------------


class Page(WireModel):
    id: int = Field(ge=1, le=604)
    key: str = Field(pattern=r"^page:[0-9]{3}$")
    start_ayah: str
    end_ayah: str
    ayah_count: int = Field(ge=1)
    ayah_ids: list[str]
    parent_ids: list[str]
    child_ids: dict[str, list[str]]
    ayahs: list[Ayah]


class MinAyah(WireModel):
    k: AyahKey = Field(pattern=r"^[1-9][0-9]{0,2}:[1-9][0-9]{0,2}$")
    t: str
    tc: str
    sj: MinSajdaType | None
    p: int = Field(ge=1, le=604)
    ps: MinAyahParents


class MinSurah(WireModel):
    i: int = Field(ge=1, le=114)
    k: str = Field(pattern=r"^surah:[0-9]{3}$")
    na: str
    nt: str
    ne: str
    rt: Literal["Meccan", "Medinan"]
    ac: int = Field(ge=1)
    rc: int = Field(ge=0)
    sa: AyahKey
    ea: AyahKey
    a: list[MinAyah]


class MinRange(WireModel):
    i: int = Field(ge=1)
    k: str
    sa: AyahKey
    ea: AyahKey
    ac: int = Field(ge=1)
    a: list[MinAyah]


class MinJuz(MinRange):
    k: str = Field(pattern=r"^juz:[0-9]{2}$")
    sc: list[str]


class MinManzil(MinRange):
    k: str = Field(pattern=r"^manzil:[0-9]{2}$")
    sc: list[str]


class MinRuku(MinRange):
    k: str = Field(pattern=r"^ruku:[0-9]{3}$")
    sh: str


class MinHizb(MinRange):
    k: str = Field(pattern=r"^hizb:[0-9]{2}$")
    ji: str


class MinRub(MinRange):
    k: str = Field(pattern=r"^rub:[0-9]{3}$")
    hi: str


class MinPage(MinRange):
    k: str = Field(pattern=r"^page:[0-9]{3}$")


class MinSajdah(WireModel):
    i: int = Field(ge=1, le=15)
    k: str = Field(pattern=r"^sajdah:[0-9]{2}$")
    ay: AyahKey
    t: MinSajdaType
    sh: str
    ad: MinAyah


class SourceMetadata(WireModel):
    source: str
    text_type: str
    ayat_count: int
    surah_count: int
    juz_count: int
    manzil_count: int
    ruku_count: int
    hizb_count: int
    rub_count: int
    page_count: int
    sajdah_count: int
    generated_at: str
    schema_version: Literal[4]
    provenance: dict[str, dict[str, Any]]


class QuranFull(WireModel):
    meta: SourceMetadata
    surahs: list[Surah]
    juz: list[Juz]
    manzil: list[Manzil]
    ruku: list[Ruku]
    hizb: list[Hizb]
    rub: list[Rub]
    pages: list[Page]
    sajdah: list[Sajdah]


class MinSourceMetadata(WireModel):
    src: str
    tt: str
    ac: int
    sc: int
    jc: int
    mnc: int
    rc: int
    hc: int
    rbc: int
    pc: int
    sac: int
    ga: str
    sv: Literal[4]
    sp: dict[str, dict[str, Any]]


class QuranFullMin(WireModel):
    m: MinSourceMetadata
    s: list[MinSurah]
    j: list[MinJuz]
    mn: list[MinManzil]
    rk: list[MinRuku]
    hz: list[MinHizb]
    rb: list[MinRub]
    pg: list[MinPage]
    sj: list[MinSajdah]


class SurahIndexChildren(WireModel):
    ayah_count: int
    ruku_count: int


class SurahIndexEntry(WireModel):
    id: int
    key: str
    name_arabic: str
    name_transliteration: str
    name_english: str
    revelation_type: Literal["Meccan", "Medinan"]
    revelation_order: int
    ayah_count: int
    ruku_count: int
    start: AyahKey
    end: AyahKey
    parents: list[str]
    children: SurahIndexChildren
    file: str


class AyahIndexEntry(WireModel):
    key: AyahKey
    id: str
    sura: int
    aya: int
    file: str


class RangeIndexEntry(WireModel):
    id: int
    key: str
    file: str
    start: AyahKey
    end: AyahKey
    ayah_count: int


class SajdahIndexEntry(WireModel):
    id: int
    key: str
    file: str
    ayah: AyahKey
    type: SajdaType


class ScopeIndex(RootModel[list[SurahIndexEntry] | list[AyahIndexEntry] | list[RangeIndexEntry] | list[SajdahIndexEntry]]):
    pass


class MinAyahIndexEntry(WireModel):
    k: AyahKey
    f: str


class MinRangeIndexEntry(WireModel):
    i: int
    k: str
    f: str
    sa: AyahKey
    ea: AyahKey
    ac: int


class MinSajdahIndexEntry(WireModel):
    i: int
    k: str
    f: str
    ay: AyahKey
    t: MinSajdaType


class ScopeIndexMin(RootModel[list[MinAyahIndexEntry] | list[MinRangeIndexEntry] | list[MinSajdahIndexEntry]]):
    pass


class RootIndex(WireModel):
    version: Literal[4]
    generated_at: str
    scopes: dict[str, str]
    totals: SourceMetadata


class RootIndexMin(WireModel):
    v: Literal[4]
    ga: str
    scopes: dict[str, str]
    totals: MinSourceMetadata
