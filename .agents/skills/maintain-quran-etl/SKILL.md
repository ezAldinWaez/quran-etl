---
name: maintain-quran-etl
description: Safely implement and verify changes to the quran-etl Python pipeline. Use when modifying Quran ingestion, configuration, parsing, normalization, graph transformation, Pydantic schemas, paired full/minified JSON emission, semantic verification, CLI behavior, or dataset documentation under data/.
---

# Maintain Quran ETL

Preserve the repository's denormalized output contract and Quran-data integrity while making pipeline changes.

## Workflow

1. Read `AGENTS.md`, then inspect the affected implementation, tests, `config/settings.yaml`, and authoritative documentation. Do not infer emitted shapes from examples alone.
2. Trace the change through every affected layer before editing:
   - Schema or full-output field: update `schemas.py`, emitter behavior, generated JSON Schemas, `docs/SCHEMA.md`, dataset READMEs, and tests.
   - Minified field or code: update `emit.py`, the key map in `data/README.md`, relevant per-scope README files, and tests together.
   - Parser or normalization behavior: preserve Tanzil text terms, configured Bismillah rules, Unicode NFC behavior, and raw-source provenance; add focused parser/normalizer tests.
   - Scope, range, or relationship: update transform, emit, and verification logic; prove count, coverage, parent/child, inline-ayah, and filename invariants.
   - CLI, config, or download behavior: preserve strict settings validation, mutually exclusive flags, request-fingerprinted caching, and atomic writes.
3. Make the smallest coherent change. Never manually edit generated Quran JSON or Quran source text.
4. Run focused tests while iterating, then run the full checks:

```bash
python -m pytest
python -m ruff check src tests
python -m quran_etl --min --clean --verify --skip-download
```

Use `--skip-download` only when the required `raw/` cache exists. Otherwise obtain the source through the normal downloader. For schema-only changes, also run `python -m quran_etl --schemas-only` and validate the generated schemas.

5. Treat every verification failure as a defect or incomplete dataset. Diagnose it; never weaken, bypass, or suppress the invariant.

## Guardrails

- Preserve all 6,236 ayahs and the expected counts for every scope.
- Keep range-bearing files self-contained with inline `ayahs`.
- Keep ruku ranges within their starting surah.
- Use underscore-based ayah filenames such as `001_001.json`; retain colon-based keys inside JSON.
- Use `--clean` rather than deleting `data/`, because tracked READMEs live there alongside both JSON variants.
- Keep Markdown prose paragraphs and list items on one physical line.
- For work under `reports/`, use the repository's `quarto-authoring`, `docx`, or `pdf` skill as appropriate and follow `reports/README.md`.
