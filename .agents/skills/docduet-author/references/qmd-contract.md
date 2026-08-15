# DocDuet authoring contract

`docduet` owns the Word-production pipeline. Quarto owns document semantics and execution.

## Commands

```bash
docduet render <entry.qmd> --output <generated.docx>
docduet publish <entry.qmd> --to html --output-dir <site-dir>
docduet publish <entry.qmd> --to epub --output-dir <book-dir>
docduet publish <entry.qmd> --to pdf --pdf-backend <word-com|aspose-cloud> --output-dir <pdf-dir>
docduet publish <document.docx> --to pdf --pdf-backend <word-com|aspose-cloud> --output-dir <pdf-dir>
```

`render` discovers the Quarto project, honors effective execution configuration, applies packaged filters and DOCX stages, validates the package, and atomically writes the output. HTML and ePub publication require QMD. PDF publication accepts QMD or DOCX; DOCX input skips rendering and goes directly to the selected converter. Every publication validates the result and replaces only a managed publication directory.

## Effective configuration

Keep native settings such as `format`, `execute`, `bibliography`, language, project type, and cross-reference options in normal Quarto configuration. Put tool settings under `docduet:` in project or document metadata:

```yaml
docduet:
  template: templates/report.docx
  content-placeholder: "[[CONTENT]]"
  figure-max-height-cm: 22.5
  page-size: A4
  features:
    diagrams: true
    localization: ar
  icons-dir: assets/icons
  semantic-styles:
    key-value: KeyValue
  callouts:
    callout-recommendation:
      title: Recommendation
      icon-symbol: fa-lightbulb

diagram:
  cache: true
  cache-dir: _cache
  engine:
    plantuml:
      execpath: plantuml
```

Paths are resolved relative to the calling Quarto project. A packaged neutral, cover-free template is used when `template` is omitted. Configure a project-owned template for branded covers or page furniture. Legacy DocDuet pre/post hooks are unsupported.

Configure derived HTML and ePub output with native Quarto fields rather than duplicating them under `docduet`:

```yaml
format:
  docx:
    toc: true
  html:
    theme: cosmo
    css: styles.css
  epub:
    css: book.css
    epub-cover-image: cover.png
```

HTML/ePub theme, template, CSS, covers, fonts, includes, and execution settings remain Quarto-owned. DocDuet adds only structural compatibility rules: code is isolated LTR inside RTL documents, figures cannot overflow their content column, custom callouts use logical borders, and Latin bibliographies are isolated from the surrounding RTL flow. HTML and ePub are derived outputs and never participate in QMD↔DOCX reconciliation. Collapsible custom callouts remain expanded in ePub because e-readers do not run Quarto's Bootstrap JavaScript.

Markdown table delimiter alignment is explicit and portable. `:---` requests left alignment and `---:` requests right alignment; use the latter (or an unaligned `---` delimiter) for Arabic text rather than expecting document direction to override an authored alignment. Size HTML figures with native Quarto figure options or project CSS; `docduet.figure-max-height-cm` remains DOCX-only.

Preview a published directory through HTTP rather than opening its entrypoint with `file://`, because browsers can block Quarto's module scripts for local files.

The optional diagram feature packages the `pandoc-ext/diagram` filter but not its external executables. Configure only engines used by the project; DocDuet validates them before rendering. Prefer Quarto-native `{mermaid}` and `{dot}` cells when possible, and enable the feature for extended class-based blocks such as `{.plantuml}`. Use `fig-cap` and `fig-alt` on diagrams. The optional `localization: ar` feature supplies Arabic Quarto UI strings; keep `lang: ar` in Quarto metadata.

## Source principles

- Use one entry QMD per invocation, with discovered includes and related source files. Do not assume that separate calling projects share content, templates, data, or lifecycle state.
- Prefer structural QMD and Quarto features over manual Word-like spacing or styling.
- Keep executable output reproducible from code, data, dependencies, and configuration.
- Use semantic styles to express meaning, not transient direct formatting.
- Preserve accessible captions, alternative text, link targets, note structure, and language/direction metadata.

Semantic class examples:

```markdown
::: {.decision}
Use the client-specific template for this deliverable.
:::

This is a [defined term]{.term}.
```

For a pandas table, prefer an explicit display that omits a meaningless index, for example `display(frame.style.hide(axis="index"))` or a Quarto/Pandoc-native table produced by the chosen execution engine. Inspect the resulting Word table rather than assuming notebook display semantics are ideal.

The packaged default template is neutral and has no cover. When a cover, branded page furniture, or template-defined back matter is required, configure an explicit template and supply every metadata field that template requires.
