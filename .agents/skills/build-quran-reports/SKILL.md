---
name: build-quran-reports
description: Author, render, reconcile, inspect, and validate this repository’s executable Quarto reports and editable DOCX deliverables. Use for files under reports/, Arabic RTL report layout, Quran semantic styles, the branded Word template, DocDuet configuration, editor-returned DOCX files, or local report smoke-test failures.
---

# Build Quran Reports

Use this repository’s Quran data and report conventions around the shared DocDuet pipeline.

## Choose the workflow

- Also use `docduet-author` when creating or changing report sources and rendering their DOCX output.
- Also use `docduet-sync` when an editor returns a revised DOCX that must be reconciled into QMD, code, data, or configuration.
- Also use `quarto-authoring` for Quarto syntax, executable cells, cross-references, figures, callouts, citations, diagrams, or native project configuration.
- Use an environment-level document skill to render the final DOCX to page images and inspect layout. Treat PDF as an explicit downstream export, not a substitute for validating the DOCX.

## Repository contract

1. Read `reports/README.md`, `reports/_quarto.yml`, and the target QMD.
2. Keep production sources in `reports/production/`, examples in `reports/examples/`, the minimal manual fixture in `reports/tests/`, project-owned assets in `reports/resources/`, and generated artifacts in `reports/output/`.
3. Keep Quarto-native configuration native. Put the template, content placeholder, figure rules, packaged Arabic localization, optional icon path, semantic styles, and custom callouts only under the effective `docduet:` block.
4. Use `.quran` for Quran spans. Extend `docduet.semantic-styles` only when the matching named style exists in the Word template; do not hard-code Word style names into QMD.
5. Build and verify generated `data/` before rendering a report that reads it. Never edit Quran source text manually or commit generated Quran JSON.
6. Treat QMD files as trusted executable code. Do not execute report changes from untrusted forks.

## Render and validate

Run from the repository root after fetching Git LFS assets and submodules:

```bash
python -m pip install -e ".[dev]" -r reports/requirements.txt
python -m quran_etl --clean --verify
docduet render reports/production/<report>.qmd --output reports/output/production/<report>.docx
```

The command must complete every packaged DocDuet stage and its DOCX package validation. Do not bypass a failed stage or patch the generated DOCX to hide a source problem. Confirm the file exists, opens as a DOCX package, and visually inspect every page for cover/content integration, Arabic shaping and RTL order, headings, Quran styles, tables, figures, callouts, fields, links, notes, page breaks, and clipping. Keep generated output untracked.

## Reconcile an edited Word file

Require the matching QMD/project/data version and preserve the returned editor DOCX exactly. Run `docduet compare` into a new directory under `reports/output/comparisons/`, inspect the manifest, source context, structured diff, comments and revision evidence, update the real source of each editorial change, rerender, and compare again into another fresh directory. Maintain `resolution.json` with an applied, intentionally-retained, deferred, or unsupported outcome for every content or semantic-style change. Never overwrite the returned DOCX or replace computed material with static content without determining whether code, data, or configuration should change instead.

## Failure handling

- Treat a Git LFS pointer in place of the Word template or morphology data as an environment failure.
- Treat missing generated `data/`, Quarto, or the headless browser required by Quarto's native Mermaid rendering as explicit prerequisites rather than silently dropping content.
- Keep report verification local because DocDuet is private. After infrastructure changes, render `reports/tests/smoke.qmd`; do not add cross-repository credentials, report execution, artifact retention, or release publishing to GitHub Actions.
