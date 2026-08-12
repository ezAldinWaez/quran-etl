# Reports

This directory is one Quarto project whose editable DOCX deliverables are produced by the headless `qmd2word` pipeline. The repository owns the report sources, Quran data, and branded Word template; the installed `qmd2word` package owns the reusable filters, Arabic UI localization, content transplant, post-processing, validation, comparison, and atomic output stages.

```text
reports/
├── production/              # real report sources
├── examples/                # reusable demonstrations
├── tests/                   # minimal manual smoke document
├── resources/
│   ├── docx/                # branded DOCX template (Git LFS)
│   ├── pptx/                # PPTX graphics template (Git LFS)
│   ├── quranic-corpus/      # Quran morphology data (Git LFS)
│   └── fonts/               # font sources (Git submodule)
├── output/                  # generated artifacts; gitignored
├── _quarto.yml              # Quarto and qmd2word configuration
├── requirements-qmd2word.txt # minimal pinned pipeline dependency
└── requirements.txt         # full local report environment
```

## Install and render

Run commands from the repository root. `reports/requirements-qmd2word.txt` and `skills-lock.json` pin the private `qmd2word` package and its two agent skills to the `v0.3.1` Git tag so local work and agent workflows use the same release contract. Installation requires GitHub access to the private qmd2word repository. `reports/requirements.txt` includes that minimal file and adds the analytics/Jupyter dependencies used by real reports.

```bash
git lfs install
git lfs pull
git submodule update --init --recursive
python -m pip install -e ".[dev,reports]" -r reports/requirements.txt
python -m quran_etl --clean --verify
python -m quran_etl render reports/production/01-quran-in-numbers.qmd --output reports/output/production/01-quran-in-numbers.docx
python -m quran_etl render reports/production/02-juz-review-map.qmd --output reports/output/production/02-juz-review-map.docx
python -m quran_etl render reports/production/03-quran-orthography.qmd --output reports/output/production/03-quran-orthography.docx
```

The production QMD contains executable Python and must be treated as trusted code. `quran-etl render` imports qmd2word and delegates to its typed Python API, which discovers this Quarto project, honors its execution settings, applies the project template and packaged stages, validates the DOCX package, and atomically writes the explicit output path. Microsoft Word is not required to render.

## Build and publish Quran data and reports

On Windows with Microsoft Word and GitHub CLI installed, the local publishing script rebuilds and verifies the paired full and minified files under `data/`, packages the single tree as `quran-data.zip`, discovers every QMD under `reports/production/`, renders DOCX files, updates Word fields through COM, exports PDFs, generates an indexed English release description, and creates or updates the repository's sole GitHub release. The dataset archive retains all 15,746 generated JSON files, the unified guides, JSON Schemas, Tanzil source attribution, and `LICENSE.txt`. The script refuses to choose destructively when more than one release exists.

```bash
python reports/scripts/publish_reports.py
```

Use `--skip-publish` to exercise the complete local dataset, DOCX, and PDF workflow without changing GitHub. Use `--skip-data` only when the existing paired `data/` tree is already current and verified; it is still validated and packaged. Run `gh auth login -h github.com` before publishing. A real publication requires a clean tracked worktree and requires local `HEAD` to equal the default branch head on GitHub; the workflow then moves the sole release tag to that exact commit and records its SHA in the release notes. Generated ZIP archives, DOCX files, PDFs, release notes, and the timestamped log stay under the gitignored `reports/output/` tree.

## Configuration ownership

Keep Quarto-native settings such as project structure, `lang`, execution, native diagrams, and DOCX format options in their normal locations. Keep tool-owned settings under the `qmd2word:` block in `_quarto.yml`: the template, content placeholder, figure limit, packaged Arabic localization, optional icon directory, semantic Word style mappings, and custom callouts. The production report uses Quarto's native Mermaid support and does not require the optional extended-diagram feature. Do not restore the old qmd2word pre/post-render hooks or copy package filters into this repository.

Use the configured semantic Quran class in QMD instead of the Word style name:

```markdown
قال تعالى: [إِنَّ مَعَ ٱلْعُسْرِ يُسْرًا]{.quran}
```

The `.quran` mapping lives under `qmd2word.semantic-styles` in `_quarto.yml` and applies the template’s `Quran` character style to inline spans. Add another semantic mapping only after its named Word style has been deliberately added to the project template.

## Word editorial round trip

The QMD project is the executable representation. A returned editor DOCX is the editorial authority for that review round. Preserve the returned file exactly and compare it with the matching QMD/project/data version in a fresh directory:

```bash
python -m quran_etl compare reports/production/03-quran-orthography.qmd path/to/editor-returned.docx --output-dir reports/output/comparisons/quran-orthography-iteration-1
```

The comparison directory contains the regenerated baseline, an untouched copy of the edited DOCX, structured source context and intermediate representations, `diff.json`, `report.html`, and extracted media. The diff is descriptive evidence; it does not prescribe QMD syntax. Use the repo-local `qmd2word-sync` skill to interpret the evidence, update the appropriate QMD, code, data, or configuration, rerender, compare into another fresh directory, and record each change as applied, intentionally retained, deferred, or unsupported. Never render over the editor-returned DOCX.

## External resources

Large report assets are stored with Git LFS: the DOCX template, the PPTX graphics template, and the Quranic Arabic Corpus morphology dataset. Run `git lfs pull` after cloning if the working tree contains pointer files instead of the actual assets.

The Scheherazade New font source is pinned to the official `v4.500` release as a Git submodule under `resources/fonts/`. The selected font is also embedded in `resources/docx/template.docx`, so the current DOCX does not depend on installing or building the font submodule.

## Manual smoke test

The report pipeline is intentionally excluded from GitHub Actions because qmd2word is private and this project does not maintain cross-repository CI credentials. After changing qmd2word configuration, the Word template, localization feature, or report infrastructure, run the small local check:

```bash
python -m quran_etl render reports/tests/smoke.qmd --output reports/output/tests/smoke.docx
```

The smoke document verifies nested-project discovery, cover injection, content transplant, Arabic RTL processing, semantic Quran styling, tables, validation, and atomic output without building Quran data or executing the production report. Production rendering also remains an explicit trusted local operation because its QMD executes code and expands to a large document.

## Conventions

- Keep report-specific logic in its QMD or deliberately included source files.
- Keep production reports in `production/`, reusable demonstrations in `examples/`, minimal integration fixtures in `tests/`, project-owned assets in `resources/`, and generated files in `output/`.
- Keep DOCX, PPTX, and the Quran morphology resource under Git LFS. Run `git lfs ls-files` before committing changes to these assets.
- Use `qmd2word-author` for report creation or source updates and `qmd2word-sync` when incorporating an editor-returned Word file.
- Treat field instructions as part of the document; Word may refresh displayed field results when an editor opens the file.
