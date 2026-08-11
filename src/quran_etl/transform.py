"""Transform stage: turn raw Tanzil records into a fully cross-referenced graph.

Tanzil metadata only gives **start** ayahs for each chunk (juz/hizb/ruku/...).
Here we expand those to inclusive ranges and emit typed models with full
parent/child linkage.
"""

from __future__ import annotations

import logging
from collections.abc import Iterable
from typing import Any

from . import normalize
from .config import Settings
from .schemas import (
    Ayah,
    Hizb,
    Juz,
    Manzil,
    Page,
    Rub,
    Ruku,
    Sajdah,
    Surah,
)

logger = logging.getLogger(__name__)


def _key(sura: int, aya: int) -> str:
    return f"{sura}:{aya}"


def _verse_order_iter(total_ayahs: int, sura_aya_counts: list[int]) -> Iterable[tuple[int, int, int]]:
    """Yield (global_id, sura, aya) in canonical reading order."""
    gid = 1
    for sura, count in enumerate(sura_aya_counts, start=1):
        for aya in range(1, count + 1):
            yield gid, sura, aya
            gid += 1
    if gid - 1 != total_ayahs:
        raise ValueError(
            f"verse count mismatch: walked {gid - 1} but expected {total_ayahs}"
        )


def _expand_range(
    start: tuple[int, int],
    end: tuple[int, int],
    sura_aya_counts: list[int],
) -> list[tuple[int, int]]:
    """Inclusive list of (sura, aya) from `start` to `end`."""
    out: list[tuple[int, int]] = []
    cur_sura, cur_aya = start
    end_sura, end_aya = end
    while True:
        max_aya = sura_aya_counts[cur_sura - 1]
        stop = end_aya if cur_sura == end_sura else max_aya
        for a in range(cur_aya, stop + 1):
            out.append((cur_sura, a))
        if cur_sura == end_sura:
            break
        cur_sura += 1
        cur_aya = 1
    return out


def _prev_ayah(key: tuple[int, int], sura_aya_counts: list[int] | None = None) -> tuple[int, int]:
    """Return the ayah immediately preceding (sura, aya).

    If `sura_aya_counts` is provided, the previous surah's last ayah is
    returned; otherwise (1, 1) is used as a conservative fallback.
    """
    s, a = key
    if a > 1:
        return (s, a - 1)
    if sura_aya_counts is not None and s - 2 >= 0:
        return (s - 1, sura_aya_counts[s - 2])
    return (s - 1, 1)


def _last_in_sura(sura: int, sura_aya_counts: list[int]) -> tuple[int, int]:
    return (sura, sura_aya_counts[sura - 1])


def _expand_until_next(
    this_start: tuple[int, int],
    next_start: tuple[int, int] | None,
    sura_aya_counts: list[int],
    *,
    constrain_to_start_sura: bool = False,
) -> list[tuple[int, int]]:
    """All ayahs from this_start up to (next_start - 1 ayah).

    If no next_start, extend to the last ayah of the Quran.
    If `constrain_to_start_sura` is True, the chunk is also clipped to
    the last ayah of `this_start`'s surah — used for ruku, which never
    crosses a surah boundary.
    """
    this_sura, _ = this_start
    end_in_sura = _last_in_sura(this_sura, sura_aya_counts)
    if next_start is None:
        last_sura = len(sura_aya_counts)
        last = (last_sura, sura_aya_counts[last_sura - 1])
    else:
        if constrain_to_start_sura and next_start[0] > this_sura:
            # The next chunk is in a later surah; this one is the last in
            # its surah, so it extends to the end of the surah.
            last = end_in_sura
        else:
            last = _prev_ayah(next_start, sura_aya_counts)
    if constrain_to_start_sura and last[0] > this_sura:
        last = end_in_sura
    if last < this_start:
        # Degenerate chunk: a single ayah at end of a surah.
        return [this_start]
    return _expand_range(this_start, last, sura_aya_counts)


def _build_surah(
    rec: dict[str, str],
    *,
    ayas: list[Ayah],
    sura_aya_counts: list[int],
    bismillah_exempt: set[int],
) -> Surah:
    sid = int(rec["index"])
    name_arabic = rec["name"].strip() or ""
    # For some encodings the name shows as '?' — we leave it as-is and
    # downstream consumers can fix names with their own Arabic source.
    tname = rec.get("tname", "").strip()
    ename = rec.get("ename", "").strip()
    rtype = rec.get("type", "").strip()
    order = int(rec.get("order", "0"))
    rukus = int(rec.get("rukus", "0"))
    aya_count = int(rec.get("ayas", "0"))

    end_sura = sid
    end_aya = aya_count
    ayah_ids = [_key(sid, a) for a in range(1, aya_count + 1)]

    return Surah(
        id=sid,
        key=f"surah:{sid:03d}",
        name_arabic=name_arabic,
        name_transliteration=tname,
        name_english=ename,
        revelation_type=rtype,
        revelation_order=order,
        ayah_count=aya_count,
        ruku_count=rukus,
        bismillah_pretext=sid not in bismillah_exempt,
        start_ayah=_key(sid, 1),
        end_ayah=_key(end_sura, end_aya),
        ayah_ids=ayah_ids,
        parent_ids=[],
        child_ids={},
        ayahs=ayas,
    )


def build_graph(
    meta: dict[str, Any],
    text: dict[tuple[int, int], str],
    settings: Settings,
) -> dict[str, Any]:
    """The big one: produce the full graph as Pydantic models."""

    # 1. Suras first (to know aya counts)
    sura_recs = meta["suras"]
    sura_aya_counts = [int(s["ayas"]) for s in sura_recs]
    total_ayahs = sum(sura_aya_counts)
    logger.info("total ayahs across all surahs: %d", total_ayahs)

    # 2. Ayahs
    ayahs: list[Ayah] = []
    ayah_by_key: dict[str, Ayah] = {}

    # Pre-compute sajda lookup
    sajda_by_ayah: dict[tuple[int, int], str] = {
        (int(s["sura"]), int(s["aya"])): s.get("type", "recommended") for s in meta["sajdas"]
    }

    # bismillah prefix handling
    bismillah_exempt = set(settings.bismillah_exempt_surahs)
    bismillah_removals = 0

    for gid, sura, aya in _verse_order_iter(total_ayahs, sura_aya_counts):
        raw = text.get((sura, aya))
        if raw is None:
            raise KeyError(f"missing text for ayah {sura}:{aya}")
        normalized_raw = normalize.normalize_arabic(raw, settings.normal_form)
        stripped = normalize.strip_marks(normalized_raw)
        # Optionally strip Bismillah from verse 1:1 of every surah except 1 and 96
        if (
            settings.strip_bismillah_from_non_fatiha
            and aya == 1
            and sura not in bismillah_exempt
        ):
            without_bismillah = normalize.strip_bismillah(stripped)
            if without_bismillah == stripped.strip():
                raise ValueError(f"expected Bismillah prefix at ayah {sura}:1")
            stripped = without_bismillah
            bismillah_removals += 1
        stripped = normalize.normalize_arabic(stripped, settings.normal_form).strip()

        sajda = sajda_by_ayah.get((sura, aya))
        ayah = Ayah(
            key=_key(sura, aya),
            id=f"ayah:{_key(sura, aya)}",
            global_id=gid,
            sura=sura,
            aya=aya,
            text=stripped,
            text_raw=normalized_raw,
            text_clean=normalize.search_text(stripped),
            char_count=normalize.char_count(stripped),
            word_count=normalize.word_count(stripped),
            sajda=sajda,  # type: ignore[arg-type]
            page=1,
            parents={},  # filled below
        )
        ayahs.append(ayah)
        ayah_by_key[ayah.key] = ayah

    if settings.strip_bismillah_from_non_fatiha:
        expected_removals = sum(
            int(record["index"]) not in bismillah_exempt for record in sura_recs
        )
        if bismillah_removals != expected_removals:
            raise AssertionError(
                f"removed {bismillah_removals} Bismillah prefixes, expected {expected_removals}"
            )
        logger.info("removed %d configured Bismillah prefixes", bismillah_removals)

    # 3. Surahs (with their ayahs grouped)
    surahs: list[Surah] = []
    ayahs_by_sura: dict[int, list[Ayah]] = {}
    for a in ayahs:
        ayahs_by_sura.setdefault(a.sura, []).append(a)
    for rec in sura_recs:
        sid = int(rec["index"])
        surahs.append(_build_surah(
            rec,
            ayas=ayahs_by_sura[sid],
            sura_aya_counts=sura_aya_counts,
            bismillah_exempt=bismillah_exempt,
        ))

    # 4. Juz, Manzil, Ruku, Page  -- they all share the same "expand start to next" logic.
    def _build_linear_records(
        records: list[dict[str, str]],
        model_cls,
        scope: str,
        key_fn,
        include_surahs_covered: bool = False,
        constrain_to_start_sura: bool = False,
    ) -> list:
        items: list = []
        for i, rec in enumerate(records):
            sid = int(rec["sura"])
            aid = int(rec["aya"])
            start = (sid, aid)
            next_start = None
            if i + 1 < len(records):
                nxt = records[i + 1]
                next_start = (int(nxt["sura"]), int(nxt["aya"]))
            verses = _expand_until_next(
                start, next_start, sura_aya_counts,
                constrain_to_start_sura=constrain_to_start_sura,
            )
            end = verses[-1]
            ayah_keys = [_key(s, a) for s, a in verses]
            kid = int(rec["index"])
            kwargs = dict(
                id=kid,
                key=key_fn(kid, sid, aid),
                start_ayah=_key(*start),
                end_ayah=_key(*end),
                ayah_count=len(verses),
                ayah_ids=ayah_keys,
                parent_ids=[],
                child_ids={},
            )
            if include_surahs_covered:
                surahs_covered = sorted({s for s, _ in verses})
                kwargs["surahs_covered"] = [f"surah:{s:03d}" for s in surahs_covered]
            if scope == "ruku":
                kwargs["surah"] = f"surah:{sid:03d}"
                kwargs["surah_id"] = f"surah:{sid:03d}"
            item = model_cls(**kwargs)
            items.append(item)
        return items

    juzs = _build_linear_records(
        meta["juzs"], Juz, "juz",
        key_fn=lambda i, s, a: f"juz:{i:02d}",
        include_surahs_covered=True,
    )
    manzils = _build_linear_records(
        meta["manzils"], Manzil, "manzil",
        key_fn=lambda i, s, a: f"manzil:{i:02d}",
        include_surahs_covered=True,
    )
    rukus = _build_linear_records(
        meta["rukus"], Ruku, "ruku",
        key_fn=lambda i, s, a: f"ruku:{i:03d}",
        constrain_to_start_sura=True,
    )
    pages = _build_linear_records(
        meta["pages"], Page, "page",
        key_fn=lambda i, s, a: f"page:{i:03d}",
    )

    # 5. Hizb + Rub: hierarchical. Rub is the 1/4 of a hizb.
    # Tanzil gives <hizb> entries (60) and <quarter> entries (240). A quarter
    # is a hizb quarter (rub el-hizb), so we wire rub -> hizb -> juz.
    hizb_recs = meta["hizbs"]
    hizbs: list[Hizb] = []
    for i, rec in enumerate(hizb_recs):
        sid = int(rec["sura"])
        aid = int(rec["aya"])
        start = (sid, aid)
        next_start = None
        if i + 1 < len(hizb_recs):
            nxt = hizb_recs[i + 1]
            next_start = (int(nxt["sura"]), int(nxt["aya"]))
        verses = _expand_until_next(start, next_start, sura_aya_counts)
        end = verses[-1]
        kid = int(rec["index"])
        hizbs.append(
            Hizb(
                id=kid,
                key=f"hizb:{kid:02d}",
                start_ayah=_key(*start),
                end_ayah=_key(*end),
                ayah_count=len(verses),
                ayah_ids=[_key(s, a) for s, a in verses],
                parent_ids=[],
                child_ids={},
                juz_id="",  # filled below
            )
        )

    rub_recs = meta["quarters"]
    rubs: list[Rub] = []
    for i, rec in enumerate(rub_recs):
        sid = int(rec["sura"])
        aid = int(rec["aya"])
        start = (sid, aid)
        next_start = None
        if i + 1 < len(rub_recs):
            nxt = rub_recs[i + 1]
            next_start = (int(nxt["sura"]), int(nxt["aya"]))
        verses = _expand_until_next(start, next_start, sura_aya_counts)
        end = verses[-1]
        kid = int(rec["index"])
        rubs.append(
            Rub(
                id=kid,
                key=f"rub:{kid:03d}",
                start_ayah=_key(*start),
                end_ayah=_key(*end),
                ayah_count=len(verses),
                ayah_ids=[_key(s, a) for s, a in verses],
                parent_ids=[],
                child_ids={},
                hizb_id="",  # filled below
            )
        )

    # 6. Sajdah — build with a placeholder ayah_data; the real one is
    # attached in step 9 once the ayah lookup is fully populated.
    sajdas: list[Sajdah] = []
    for rec in meta["sajdas"]:
        sid = int(rec["sura"])
        aid = int(rec["aya"])
        kid = int(rec["index"])
        placeholder = Ayah(
            key=_key(sid, aid),
            id=f"ayah:{_key(sid, aid)}",
            global_id=0,
            sura=sid,
            aya=aid,
            text="",
            text_raw="",
            text_clean="",
            char_count=0,
            word_count=0,
            sajda=rec.get("type", "recommended"),  # type: ignore[arg-type]
            page=1,
            parents={},
        )
        sajdas.append(
            Sajdah(
                id=kid,
                key=f"sajdah:{kid:02d}",
                ayah=_key(sid, aid),
                ayah_id=f"ayah:{_key(sid, aid)}",
                type=rec.get("type", "recommended"),  # type: ignore[arg-type]
                surah=f"surah:{sid:03d}",
                surah_id=f"surah:{sid:03d}",
                parent_ids=[],
                child_ids={},
                ayah_data=placeholder,
            )
        )

    # 7. Build authoritative numeric-order membership maps, then derive all
    # parent and child references from membership rather than string ordering.
    scope_nodes = {
        "juz": juzs,
        "manzil": manzils,
        "ruku": rukus,
        "hizb": hizbs,
        "rub": rubs,
        "page": pages,
    }

    def _membership(nodes: list) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for node in nodes:
            for ayah_key in node.ayah_ids:
                if ayah_key in result:
                    raise ValueError(
                        f"ayah {ayah_key} belongs to both {result[ayah_key].key} and {node.key}"
                    )
                result[ayah_key] = node
        if set(result) != set(ayah_by_key):
            missing = sorted(set(ayah_by_key) - set(result))
            extra = sorted(set(result) - set(ayah_by_key))
            raise ValueError(
                f"partition coverage mismatch: missing={missing[:5]}, extra={extra[:5]}"
            )
        return result

    memberships = {scope: _membership(nodes) for scope, nodes in scope_nodes.items()}
    surah_by_id = {s.id: s for s in surahs}

    for a in ayahs:
        a.parents = {"surah": surah_by_id[a.sura].key}
        for scope in ("juz", "manzil", "ruku", "hizb", "rub", "page"):
            a.parents[scope] = memberships[scope][a.key].key
        a.page = memberships["page"][a.key].id

    def _unique_members(keys: list[str], scope: str) -> list[str]:
        return list(dict.fromkeys(memberships[scope][key].key for key in keys))

    for sura in surahs:
        for scope in ("juz", "manzil", "ruku", "hizb", "rub", "page"):
            sura.child_ids[scope] = _unique_members(sura.ayah_ids, scope)
        sura.child_ids["ayah"] = [f"ayah:{key}" for key in sura.ayah_ids]

    for juz in juzs:
        juz.child_ids["hizb"] = _unique_members(juz.ayah_ids, "hizb")
        juz.child_ids["ayah"] = [f"ayah:{key}" for key in juz.ayah_ids]
        juz.parent_ids = []

    for manzil in manzils:
        manzil.child_ids["ayah"] = [f"ayah:{key}" for key in manzil.ayah_ids]
        manzil.parent_ids = []

    for ruku in rukus:
        ruku.child_ids["ayah"] = [f"ayah:{key}" for key in ruku.ayah_ids]
        ruku.parent_ids = [ruku.surah_id]

    for hizb in hizbs:
        parent_juz = memberships["juz"][hizb.start_ayah]
        hizb.juz_id = parent_juz.key
        hizb.parent_ids = [parent_juz.key]
        hizb.child_ids["rub"] = _unique_members(hizb.ayah_ids, "rub")
        hizb.child_ids["ayah"] = [f"ayah:{key}" for key in hizb.ayah_ids]

    for rub in rubs:
        parent_hizb = memberships["hizb"][rub.start_ayah]
        parent_juz = memberships["juz"][rub.start_ayah]
        rub.hizb_id = parent_hizb.key
        rub.parent_ids = [parent_hizb.key, parent_juz.key]
        rub.child_ids["ayah"] = [f"ayah:{key}" for key in rub.ayah_ids]

    for page in pages:
        page.child_ids["ayah"] = [f"ayah:{key}" for key in page.ayah_ids]
        page.parent_ids = []

    for sajda in sajdas:
        sajda.parent_ids = [
            next((s.key for s in surahs if s.id == int(sajda.ayah.split(":")[0])), "")
        ]
        sajda.child_ids["ayah"] = [sajda.ayah_id]

    # 9. Denormalize: attach the full list of inline Ayah objects to every
    # range-bearing node (and a single `ayah_data` for sajdah). This makes
    # each per-scope file self-contained for analytics — no joins, no
    # lookups, no cross-references required to access the actual Quran text.
    def _range_ayahs(start: str, end: str) -> list[Ayah]:
        out: list[Ayah] = []
        cur = ayah_by_key.get(start)
        end_ayat = ayah_by_key.get(end)
        if cur is None or end_ayat is None:
            raise KeyError(f"ayah range {start}..{end} not in ayah_by_key")
        for a in ayahs:
            if a.global_id >= cur.global_id and a.global_id <= end_ayat.global_id:
                out.append(a)
        return out

    for s in surahs:
        s.ayahs = list(ayahs_by_sura.get(s.id, []))
    for n in juzs:
        n.ayahs = _range_ayahs(n.start_ayah, n.end_ayah)
    for n in manzils:
        n.ayahs = _range_ayahs(n.start_ayah, n.end_ayah)
    for n in rukus:
        n.ayahs = _range_ayahs(n.start_ayah, n.end_ayah)
    for n in hizbs:
        n.ayahs = _range_ayahs(n.start_ayah, n.end_ayah)
    for n in rubs:
        n.ayahs = _range_ayahs(n.start_ayah, n.end_ayah)
    for n in pages:
        n.ayahs = _range_ayahs(n.start_ayah, n.end_ayah)
    for s in sajdas:
        s.ayah_data = ayah_by_key[s.ayah]

    return {
        "ayahs": ayahs,
        "surahs": surahs,
        "juzs": juzs,
        "manzils": manzils,
        "rukus": rukus,
        "hizbs": hizbs,
        "rubs": rubs,
        "pages": pages,
        "sajdas": sajdas,
        "ayah_by_key": ayah_by_key,
    }
