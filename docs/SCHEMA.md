# Schema Reference

Every JSON document in `data/` follows one of the Pydantic wire models in `src/quran_etl/schemas.py`. Paired token-minimized documents use the same basename with `.min.json`; the short-key map is documented in `data/README.md`. Machine-readable JSON Schema 2020-12 documents for full and minified items, scope indexes, root indexes, and unified Quran files live in `docs/json-schema/`. `all.schema.json` is a bundle whose root accepts any one of these public document types.

This document is the human-readable companion.

## Denormalized shape

The dataset is **denormalized for analytics**. Every range-bearing scope (surah, juz, manzil, hizb, rub, ruku, page) carries the **full inline list of Ayah objects** under the `ayahs` field. The single-ayah scope (sajdah) carries the full Ayah under `ayah_data`. This means:

- Any single file is fully self-contained. Load `data/juz/01.json` and you have every verse of Juz 1 with text, metadata, and parent references — no joins, no lookups, no cross-references to chase.
- The cost is intentional redundancy: the same Ayah object appears in many files. The full dataset is ~123 MB on disk (~100 MiB logical); `quran.full.json` alone is ~50 MB.

## Conventions

- **Surah/ayah coordinates** are unpadded in ayah keys and IDs (`2:255`, `ayah:2:255`) but zero-padded to 3 digits in ayah filenames (`data/ayah/002_255.json`). Scope keys use their documented fixed widths, such as `surah:007`, because they are also used as stable scope identifiers. Filenames use `_` instead of `:` because Windows forbids `:` in filenames.
- **Global ids** (`global_id` on Ayah) are 1-indexed, in canonical reading order: 1:1 → 1, 1:2 → 2, …, 114:6 → 6,236.
- **Cross-references** use the format `"<scope>:<key>"`:
  - `surah:001`
  - `ayah:2:255`
  - `juz:01`, `juz:02`, …, `juz:30`
  - `manzil:01` … `manzil:07`
  - `hizb:01` … `hizb:60`
  - `rub:001` … `rub:240`
  - `ruku:001` … `ruku:556`
  - `page:001` … `page:604`
  - `sajdah:01` … `sajdah:15`
- **Paired files** use `<name>.json` for the full model and `<name>.min.json` for its token-minimized equivalent. Scope indexes follow the same `index.json` and `index.min.json` convention.

## Machine-readable schemas

- `<scope>.schema.json` and `<scope>.min.schema.json` validate full and minified item documents.
- `scope-index.schema.json` and `scope-index.min.schema.json` validate the corresponding indexes in each scope directory.
- `index.schema.json` and `index.min.schema.json` validate the two root manifests.
- `quran.full.schema.json` and `quran.full.min.schema.json` validate the unified dataset documents.
- `all.schema.json` bundles every public document schema and validates any one document type at its root.

---

## Ayah (`data/ayah/<sura:03>_<aya:03>.json`)

The leaf of the tree. One file per verse.

| field        | type           | description                                                                                                                       |
| ------------ | -------------- | --------------------------------------------------------------------------------------------------------------------------------- |
| `key`        | string         | `"<sura>:<aya>"`, e.g. `"2:255"`                                                                                                  |
| `id`         | string         | `"ayah:<sura>:<aya>"`, e.g. `"ayah:2:255"`                                                                                        |
| `global_id`  | int            | 1-indexed position in canonical reading order                                                                                     |
| `sura`       | int            | 1..114                                                                                                                            |
| `aya`        | int            | 1..N (N depends on the surah)                                                                                                     |
| `text`       | string         | Uthmani Arabic, NFC-normalized, with sajdah marks `۩` and rub marks `۞` removed; Bismillah prefix stripped from non-exempt surahs |
| `text_raw`   | string         | Uthmani Arabic exactly as Tanzil delivered it, NFC-normalized                                                                     |
| `text_clean` | string         | Diacritics + marks removed; suitable for substring search                                                                         |
| `char_count` | int            | Codepoint length of `text`                                                                                                        |
| `word_count` | int            | Whitespace-delimited tokens (tatweel is treated as in-word glue)                                                                  |
| `sajda`      | string \| null | `"obligatory"` \| `"recommended"` \| `null`                                                                                       |
| `page`       | int            | 1..604 — Madina Mushaf page number                                                                                                |
| `parents`    | object         | Map of `scope → "<scope>:<key>"` containing this ayah. Always has: `surah`, `juz`, `manzil`, `ruku`, `hizb`, `rub`, `page`.       |

## Surah (`data/surah/<NNN>.json`)

| field                  | type         | description                                                                                                                                          |
| ---------------------- | ------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------- |
| `id`                   | int          | 1..114                                                                                                                                               |
| `key`                  | string       | `"surah:<NNN>"` (3-digit padding)                                                                                                                    |
| `name_arabic`          | string       | Arabic surah name                                                                                                                                    |
| `name_transliteration` | string       | e.g. `"Al-Baqara"`                                                                                                                                   |
| `name_english`         | string       | e.g. `"The Cow"`                                                                                                                                     |
| `revelation_type`      | string       | `"Meccan"` \| `"Medinan"`                                                                                                                            |
| `revelation_order`     | int          | 1..114 — chronological order of revelation                                                                                                           |
| `ayah_count`           | int          | Number of ayahs in this surah                                                                                                                        |
| `ruku_count`           | int          | Number of ruku sections                                                                                                                              |
| `bismillah_pretext`    | bool         | Whether the surah has an "extra" Bismillah as a _prefix_ to 1:1 (true for every surah except 1, 9, 96)                                               |
| `start_ayah`           | string       | `"<sura>:1"`                                                                                                                                         |
| `end_ayah`             | string       | `"<sura>:<last_aya>"`                                                                                                                                |
| `ayah_ids`             | list[string] | All ayah keys belonging to this surah (convenience summary)                                                                                          |
| `parent_ids`           | list[string] | Always `[]` for surahs (they are the top-level units)                                                                                                |
| `child_ids`            | object       | Map of `scope → [keys]`. Includes: `juz`, `manzil`, `ruku`, `hizb`, `rub`, `page`, `ayah`                                                            |
| `ayahs`                | list[Ayah]   | **Inline denormalized** list of all Ayah objects in this surah. The whole point of the denormalized shape: every scope file carries the actual text. |

## Juz (`data/juz/<NN>.json`)

| field            | type         | description                                                   |
| ---------------- | ------------ | ------------------------------------------------------------- |
| `id`             | int          | 1..30                                                         |
| `key`            | string       | `"juz:<NN>"`                                                  |
| `start_ayah`     | string       | First ayah                                                    |
| `end_ayah`       | string       | Last ayah                                                     |
| `ayah_count`     | int          |                                                               |
| `ayah_ids`       | list[string] | Convenience summary of the ayah keys in this juz              |
| `parent_ids`     | list[string] | Always `[]`; juz is an independent top-level partition         |
| `child_ids`      | object       | Includes `hizb` and `ayah`                                    |
| `surahs_covered` | list[string] | Surah keys fully or partially inside this juz                 |
| `ayahs`          | list[Ayah]   | **Inline denormalized** list of full Ayah objects in this juz |

## Manzil (`data/manzil/<NN>.json`)

Same shape as Juz. 7 entries. `parent_ids = []`. Carries inline `ayahs`.

## Ruku (`data/ruku/<NNN>.json`)

| field                     | type         | description                                                            |
| ------------------------- | ------------ | ---------------------------------------------------------------------- |
| `id`                      | int          | 1..556                                                                 |
| `key`                     | string       | `"ruku:<NNN>"`                                                         |
| `start_ayah` / `end_ayah` | string       | Ruku never crosses a surah boundary, so both are within the same surah |
| `ayah_count`              | int          |                                                                        |
| `ayah_ids`                | list[string] | Convenience summary                                                    |
| `parent_ids`              | list[string] | `["surah:<NNN>"]` — the containing surah                               |
| `child_ids`               | object       | `{"ayah": [...]}`                                                      |
| `surah` / `surah_id`      | string       | Containing surah key                                                   |
| `ayahs`                   | list[Ayah]   | **Inline denormalized** list of full Ayah objects in this ruku         |

## Hizb (`data/hizb/<NN>.json`)

| field                     | type         | description                                                    |
| ------------------------- | ------------ | -------------------------------------------------------------- |
| `id`                      | int          | 1..60                                                          |
| `key`                     | string       | `"hizb:<NN>"`                                                  |
| `start_ayah` / `end_ayah` | string       |                                                                |
| `ayah_count`              | int          |                                                                |
| `ayah_ids`                | list[string] | Convenience summary                                            |
| `parent_ids`              | list[string] | `["juz:<NN>"]` — containing juz                                |
| `child_ids`               | object       | `{"rub": [...], "ayah": [...]}`                                |
| `juz_id`                  | string       | Containing juz key                                             |
| `ayahs`                   | list[Ayah]   | **Inline denormalized** list of full Ayah objects in this hizb |

## Rub (`data/rub/<NNN>.json`) _(Hizb quarter)_

| field                     | type         | description                                                   |
| ------------------------- | ------------ | ------------------------------------------------------------- |
| `id`                      | int          | 1..240                                                        |
| `key`                     | string       | `"rub:<NNN>"`                                                 |
| `start_ayah` / `end_ayah` | string       |                                                               |
| `ayah_count`              | int          |                                                               |
| `ayah_ids`                | list[string] | Convenience summary                                           |
| `parent_ids`              | list[string] | `["hizb:<NN>", "juz:<NN>"]`                                   |
| `child_ids`               | object       | `{"ayah": [...]}`                                             |
| `hizb_id`                 | string       | Containing hizb key                                           |
| `ayahs`                   | list[Ayah]   | **Inline denormalized** list of full Ayah objects in this rub |

## Page (`data/page/<NNN>.json`)

| field                     | type         | description                                                    |
| ------------------------- | ------------ | -------------------------------------------------------------- |
| `id`                      | int          | 1..604                                                         |
| `key`                     | string       | `"page:<NNN>"`                                                 |
| `start_ayah` / `end_ayah` | string       | Madina Mushaf pagination                                       |
| `ayah_count`              | int          |                                                                |
| `ayah_ids`                | list[string] | Convenience summary                                            |
| `parent_ids`              | list[string] | Always `[]`; page is an independent top-level partition         |
| `child_ids`               | object       | `{"ayah": [...]}`                                              |
| `ayahs`                   | list[Ayah]   | **Inline denormalized** list of full Ayah objects on this page |

## Sajdah (`data/sajdah/<NN>.json`)

A point, not a range.

| field                | type         | description                                                                                                                                                                 |
| -------------------- | ------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `id`                 | int          | 1..15                                                                                                                                                                       |
| `key`                | string       | `"sajdah:<NN>"`                                                                                                                                                             |
| `ayah`               | string       | `"<sura>:<aya>"`                                                                                                                                                            |
| `ayah_id`            | string       | `"ayah:<sura>:<aya>"`                                                                                                                                                       |
| `type`               | string       | `"obligatory"` \| `"recommended"`                                                                                                                                           |
| `surah` / `surah_id` | string       | Containing surah key                                                                                                                                                        |
| `parent_ids`         | list[string] | `["surah:<NNN>"]`                                                                                                                                                           |
| `child_ids`          | object       | `{"ayah": ["ayah:<sura>:<aya>"]}`                                                                                                                                           |
| `ayah_data`          | Ayah         | **Inline denormalized** — the single Ayah object this sajdah points to. (Range-bearing scopes use `ayahs`; sajdah uses `ayah_data` because it points to exactly one verse.) |

---

## `quran.full.json`

Single denormalized file for one-shot LLM ingestion.

```jsonc
{
  "meta": {
    "source": "tanzil.net",
    "text_type": "uthmani",
    "ayat_count": 6236,
    "surah_count": 114,
    "juz_count": 30,
    "manzil_count": 7,
    "ruku_count": 556,
    "hizb_count": 60,
    "rub_count": 240,
    "page_count": 604,
    "sajdah_count": 15,
    "generated_at": "2026-06-24T12:39:24+00:00",
    "schema_version": 4,
    "provenance": {
      "metadata": { "url": "…", "request_sha256": "…", "content_sha256": "…" },
      "text": { "url": "…", "request_sha256": "…", "content_sha256": "…" }
    },
  },
  "surahs": [
    /* 114 Surah objects, each with inline `ayahs` */
  ],
  "juz": [
    /* 30, each with inline `ayahs` */
  ],
  "manzil": [
    /* 7,  each with inline `ayahs` */
  ],
  "ruku": [
    /* 556, each with inline `ayahs` */
  ],
  "hizb": [
    /* 60, each with inline `ayahs` */
  ],
  "rub": [
    /* 240, each with inline `ayahs` */
  ],
  "pages": [
    /* 604, each with inline `ayahs` */
  ],
  "sajdah": [
    /* 15, each with `ayah_data` */
  ],
}
```

Every scope is fully denormalized: each entry has its `ayahs` (or `ayah_data` for sajdah) inline, with no missing references.

---

## Counts (verified)

| scope  | count | source                                  |
| ------ | ----- | --------------------------------------- |
| surah  | 114   | metadata                                |
| ayah   | 6,236 | metadata + text                         |
| juz    | 30    | metadata                                |
| manzil | 7     | metadata                                |
| ruku   | 556   | metadata                                |
| hizb   | 60    | derived (every 4 quarters)              |
| rub    | 240   | metadata                                |
| page   | 604   | metadata (Medina Mushaf)                |
| sajdah | 15    | metadata (11 recommended, 4 obligatory) |
