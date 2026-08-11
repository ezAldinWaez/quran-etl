# qmd2word comparison contract

Run `qmd2word compare <entry.qmd> <edited.docx> --output-dir <empty-dir>`. The command regenerates the baseline and never mutates either input.

## Bundle

```text
<output-dir>/
├── manifest.json
├── documents/baseline.docx
├── documents/edited.docx
├── source-context.json
├── ir/baseline.json
├── ir/edited-accepted.json
├── ir/edited-with-revisions.json
├── diff.json
├── report.html
└── media/
```

`source-context.json` maps the entry and discovered sources and records generated block anchors. `edited-accepted.json` represents intended final content. `edited-with-revisions.json`, `diff.json.revision_evidence`, and `diff.json.comments` preserve editorial evidence separately.

## Diff meaning

Each `changes[]` item has a stable `id`, `category`, `operation`, `location`, `before`, and `after`; aligned blocks also report the alignment method. Categories include content, structure, style, style definitions, tables, links, notes, images, fields, and comments. Operations are descriptive insertions, deletions, moves, or replacements.

Anchors align generated blocks when Word preserves them. Structural and text similarity provide fallback alignment after anchor loss or for new content. A fallback match is evidence, not certainty; inspect nearby blocks when the interpretation matters.

Unanchored insertions near references, floating objects, cover/back matter, or section boundaries require special care. Use both ASTs and nearby stable anchors to decide whether the content belongs in QMD, metadata, or a template. Defer with a question when those sources remain indistinguishable.

The comparator intentionally does not propose QMD syntax. It suppresses volatile Word metadata and cached field results while preserving meaningful field instructions, relationships, media hashes, semantic/direct formatting, tracked revisions, and comments.

## Resolution record

Maintain a machine-readable `resolution.json`, for example:

```json
{
  "schema_version": 1,
  "resolutions": [
    {
      "change_ids": ["chg-example"],
      "status": "applied",
      "source_files": ["index.qmd"],
      "rationale": "Updated the authored heading.",
      "verification": "Absent from iteration-2/diff.json"
    }
  ]
}
```

Allowed statuses are `applied`, `intentionally-retained`, `deferred`, and `unsupported`. A change is reconciled only when it disappears after rerendering or has an explicit non-applied resolution.

When a rerender replaces an original change with a representation-only delta—such as direct bold versus bold inherited from a heading style—record both generations of diff IDs. Treat it as `intentionally-retained` only when the visible and semantic result is equivalent and no editorial intent is lost.
