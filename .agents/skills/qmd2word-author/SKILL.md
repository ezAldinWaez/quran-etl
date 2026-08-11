---
name: qmd2word-author
description: Create or update a Quarto QMD project whose reproducible, editable Word output is rendered by qmd2word. Use when an agent must turn user inputs into an entry .qmd, includes, code, data/config references, semantic styles, callouts, figures, tables, citations, or cross-references and verify the resulting DOCX.
---

# Author qmd2word QMD

Build the calling project's executable QMD representation, then use `qmd2word render` as its DOCX production interface. Treat qmd2word as shared infrastructure; do not invent an organization-wide adoption process or mix state between unrelated projects.

## Workflow

1. Inspect the user's inputs, intended use, entry QMD, `_quarto.yml`, includes, executable cells, data dependencies, bibliography, and selected Word template. Read [references/qmd-contract.md](references/qmd-contract.md) before changing configuration.
2. Identify the project root with `quarto inspect <entry.qmd>`. Preserve native Quarto document and execution settings. Put tool-owned settings only in the effective `qmd2word:` metadata block. Enable packaged diagrams or Arabic localization only through `qmd2word.features` when the project needs them.
3. Create or update the entry QMD and relevant included project files. Prefer meaningful Quarto structures over visual workarounds:
   - headings, lists, tables, captions, notes, links, citations, and cross-references;
   - executable cells for computed material;
   - semantic styles and configured callouts for domain meaning;
   - language and direction metadata for RTL or multilingual content.
   Apply a configured semantic block class with fenced-div syntax such as `::: {.decision}`. Apply a semantic inline class with `[text]{.decision}` when the mapping defines an inline style.
4. Keep generated content reproducible. Change source code, data, or configuration when those are the true source; do not paste computed output back as static content merely to match a rendering.
   For tabular executable output, emit a deliberate table representation and suppress accidental dataframe indexes unless the index has meaning.
5. Render non-interactively:

   ```bash
   qmd2word render path/to/entry.qmd --output path/to/generated.docx
   ```

6. Read the command result and correct source, execution, template, or configuration failures. Never patch the generated DOCX to hide a QMD problem.
7. Inspect the completed DOCX for content and layout when visual fidelity matters. Render it to PDF/page images with the environment's document-rendering workflow or headless LibreOffice, then confirm that headings, callouts, tables, figures, fields, links, notes, semantic styles, and RTL content behave as intended.
8. Report the entry QMD, files changed, render output, validation status, and any unresolved limitation.

## Boundaries

- Treat QMD and its project files as the executable representation.
- Treat a rendered DOCX as an artifact until an editor returns a revised copy; use `$qmd2word-sync` for that reconciliation workflow.
- Do not add Quarto pre/post hooks for qmd2word, call package internals, or rely on environment-variable orchestration.
- Do not add history, locking, or merge behavior. The caller owns version correspondence and concurrency.
- Operate on one Quarto entry QMD per render. Includes and related project sources are in scope.
- For mixed-direction documents, set document-level direction only when it is the dominant direction. Mark opposite-direction spans/divs explicitly and verify their Word paragraph/run properties; do not assume language metadata alone sets direction.
