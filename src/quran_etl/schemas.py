"""Pydantic models for the entire Quran data graph.

Every node carries stable `id` + `key` and full parent/child cross-references,
and the actual Quran text is **denormalized** inline so each per-scope
file is fully self-contained for analytics — no joins, no lookups.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

# ---------- Leaf: Ayah -----------------------------------------------------


class Ayah(BaseModel):
    """A single Quranic verse — the leaf of the tree."""

    model_config = ConfigDict(extra="forbid")

    key: str  # e.g. "2:255"
    id: str  # e.g. "ayah:2:255"
    global_id: int
    sura: int
    aya: int
    text: str  # normalized Uthmani (or whatever text-type)
    text_raw: str  # exactly as Tanzil delivered it
    text_clean: str  # search-friendly, no diacritics
    char_count: int
    word_count: int
    sajda: SajdaType | None = None
    page: int
    parents: dict[str, str]  # scope -> key (e.g. "surah": "surah:002")


SajdaType = Literal["obligatory", "recommended"]


# ---------- Surah ---------------------------------------------------------


class Surah(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: int
    key: str  # "surah:001"
    name_arabic: str
    name_transliteration: str
    name_english: str
    revelation_type: str  # Meccan | Medinan
    revelation_order: int
    ayah_count: int
    ruku_count: int
    bismillah_pretext: bool
    start_ayah: str
    end_ayah: str
    ayah_ids: list[str]
    parent_ids: list[str]
    child_ids: dict[str, list[str]] = Field(default_factory=dict)
    # denormalized: full inline ayahs (always present)
    ayahs: list[Ayah] = Field(default_factory=list)


# ---------- Juz -----------------------------------------------------------


class Juz(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: int
    key: str  # "juz:01"
    start_ayah: str
    end_ayah: str
    ayah_count: int
    ayah_ids: list[str]
    parent_ids: list[str]
    child_ids: dict[str, list[str]] = Field(default_factory=dict)
    surahs_covered: list[str]
    # denormalized: full inline ayahs
    ayahs: list[Ayah] = Field(default_factory=list)


# ---------- Manzil --------------------------------------------------------


class Manzil(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: int
    key: str
    start_ayah: str
    end_ayah: str
    ayah_count: int
    ayah_ids: list[str]
    parent_ids: list[str]
    child_ids: dict[str, list[str]] = Field(default_factory=dict)
    surahs_covered: list[str]
    # denormalized
    ayahs: list[Ayah] = Field(default_factory=list)


# ---------- Sajdah -------------------------------------------------------


class Sajdah(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: int
    key: str  # "sajdah:01"
    ayah: str  # e.g. "22:18"
    ayah_id: str
    type: SajdaType
    surah: str
    surah_id: str
    parent_ids: list[str]
    child_ids: dict[str, list[str]] = Field(default_factory=dict)
    # denormalized: the single ayah it points to (full object)
    ayah_data: Ayah


# ---------- Ruku ----------------------------------------------------------


class Ruku(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: int
    key: str
    start_ayah: str
    end_ayah: str
    ayah_count: int
    ayah_ids: list[str]
    parent_ids: list[str]
    child_ids: dict[str, list[str]] = Field(default_factory=dict)
    surah: str
    surah_id: str
    # denormalized
    ayahs: list[Ayah] = Field(default_factory=list)


# ---------- Hizb ---------------------------------------------------------


class Hizb(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: int
    key: str  # "hizb:01"
    start_ayah: str
    end_ayah: str
    ayah_count: int
    ayah_ids: list[str]
    parent_ids: list[str]
    child_ids: dict[str, list[str]] = Field(default_factory=dict)
    juz_id: str
    # denormalized
    ayahs: list[Ayah] = Field(default_factory=list)


# ---------- Rub (Hizb quarter) -------------------------------------------


class Rub(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: int
    key: str  # "rub:001"
    start_ayah: str
    end_ayah: str
    ayah_count: int
    ayah_ids: list[str]
    parent_ids: list[str]
    child_ids: dict[str, list[str]] = Field(default_factory=dict)
    hizb_id: str
    # denormalized
    ayahs: list[Ayah] = Field(default_factory=list)


# ---------- Page ---------------------------------------------------------


class Page(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: int
    key: str
    start_ayah: str
    end_ayah: str
    ayah_count: int
    ayah_ids: list[str]
    parent_ids: list[str]
    child_ids: dict[str, list[str]] = Field(default_factory=dict)
    # denormalized
    ayahs: list[Ayah] = Field(default_factory=list)
