# AGENTS.md

Python 3.11+ ETL pipeline from Tanzil.net Quran sources to one Arabic-only, denormalized `data/` tree with paired full-key `*.json` and short-key `*.min.json` files. Both editions cover surah, ayah, juz, manzil, hizb, rub, ruku, page, and sajdah.

## Commands

```bash
python -m pip install -e ".[dev]"
python -m quran_etl                            # emit data/
python -m quran_etl --min --verify             # emit both variants + verify
python -m quran_etl --min --clean --verify     # safely rebuild generated JSON
python -m pytest
python -m ruff check src tests
```

Use `--force-download` to refresh the `raw/` cache. Use `--schemas-only` to regenerate `docs/json-schema/`. See `python -m quran_etl --help` for all flags.

## Code map

- `src/quran_etl/cli.py`: entrypoint and safe JSON cleanup
- `config.py`, `download.py`, `parse.py`, `normalize.py`: ingestion
- `transform.py`: range expansion and parent/child wiring
- `schemas.py`, `schemas_emit.py`: Pydantic models and JSON Schema export
- `emit.py`: paired full-key and short-key output
- `verify.py`: semantic verification of both output variants
- `io_utils.py`: atomic writes
- `config/settings.yaml`: pipeline configuration
- `tests/`: unit, end-to-end, schema, and corruption-rejection coverage
- `reports/`: executable Quarto sources and DocDuet DOCX workflow; follow `reports/README.md`
- `.agents/skills/`: repo-local ETL/report workflows plus pinned Quarto, DocDuet authoring, and Word-reconciliation skills

## Required invariants

- Counts: 114 surah, 6,236 ayah, 30 juz, 7 manzil, 60 hizb, 240 rub, 556 ruku, 604 page, and 15 sajdah.
- Every partition covers all 6,236 ayahs exactly once.
- Parent maps, scope parents, child lists, page scalars, inline ayah ranges, and sajdah references must remain semantically correct.
- Ruku ranges never cross a surah boundary.
- Bismillah is stripped from the first ayah except for configured exemptions (currently surahs 1, 9, and 96); every configured removal must succeed.
- Quran text remains verbatim apart from configured normalization. Never edit the source text manually; preserve Tanzil attribution and terms.

Do not suppress verification failures; investigate incomplete or inconsistent output.

## Change rules

- Use Pydantic v2 models and keep Ruff clean. Do not add code comments unless requested.
- Keep each Markdown prose paragraph or list item on one physical line; do not hard-wrap it.
- Never use `:` in filenames. Ayah files use `001_001.json`; JSON keys retain the `1:1` form.
- Keep inline `ayahs` in every range-bearing scope file; the redundancy is intentional for self-contained analytics.
- When changing a schema or field, update `schemas.py`, relevant emitters, public docs/schemas, and tests.
- When changing a minified key, update `emit.py`, the key map in `data/README.md`, and tests together.
- Never delete the whole `data/` tree; tracked READMEs live there. Use `--clean`, which removes only selected generated JSON variants.
- Do not commit generated JSON under `data/`, `raw/`, or report outputs.

For output shapes and licensing details, use `docs/SCHEMA.md`, `data/README.md`, and `docs/SOURCES.md` as the authoritative references.
