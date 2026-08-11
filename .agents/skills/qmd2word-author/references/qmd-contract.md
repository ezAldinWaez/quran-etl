# qmd2word authoring contract

`qmd2word` owns the Word-production pipeline. Quarto owns document semantics and execution.

## Commands

```bash
qmd2word render <entry.qmd> --output <generated.docx>
```

The command discovers the Quarto project, honors effective execution configuration, applies packaged filters and DOCX stages, validates the package, and atomically writes the output.

## Effective configuration

Keep native settings such as `format`, `execute`, `bibliography`, language, project type, and cross-reference options in normal Quarto configuration. Put tool settings under `qmd2word:` in project or document metadata:

```yaml
qmd2word:
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

Paths are resolved relative to the calling Quarto project. A packaged neutral, cover-free template is used when `template` is omitted. Configure a project-owned template for branded covers or page furniture. Legacy qmd2word pre/post hooks are unsupported.

The optional diagram feature packages the `pandoc-ext/diagram` filter but not its external executables. Configure only engines used by the project; qmd2word validates them before rendering. Prefer Quarto-native `{mermaid}` and `{dot}` cells when possible, and enable the feature for extended class-based blocks such as `{.plantuml}`. Use `fig-cap` and `fig-alt` on diagrams. The optional `localization: ar` feature supplies Arabic Quarto UI strings; keep `lang: ar` in Quarto metadata.

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
