# DocDuet comparison contract

Prefer the exact review baseline:

```text
docduet compare <baseline.docx> <edited.docx> \
  --output-dir <empty-dir>
```

The command never mutates its inputs. The baseline may instead be an
`<entry.qmd>`; DocDuet then renders it and records that mode in the manifest.

## Lean bundle (default)

```text
<output-dir>/
├── manifest.json
├── diff.json
└── report.html
```

`source-context.json` is also included when the baseline is QMD.

Use `--evidence full` for portable forensic evidence. It additionally includes
the baseline and edited DOCX, accepted IR, revision-preserving IR only when
tracked revisions exist, and content-addressed media shared by all IR views.

## Diff meaning

`diff.json` schema 2 groups all related facets at one location. Each change has
a stable `id`, `operation`, `classification`, `categories`, `location`, and
`facets`. Each facet identifies its exact `field`, `category`, `classification`,
`before`, and `after` value.

`editorial` changes may require a QMD, include, code, data, configuration,
bibliography, resource, or template update. `document-only` changes preserve
meaningful Word formatting evidence that may not map to QMD. Serialization-only
Word differences are omitted from `changes` and counted under
`diagnostics.suppressed`.

Anchors align generated blocks when Word preserves them. Structural and text
similarity provide fallback alignment after anchor loss or for new content. A
fallback match is evidence, not certainty; inspect nearby blocks when the
interpretation matters.

The comparator deliberately does not propose QMD syntax. The synchronization
agent decides the appropriate executable source representation.

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

Allowed statuses are `applied`, `intentionally-retained`, `deferred`, and
`unsupported`. A change is reconciled only when it disappears after rerendering
or has an explicit non-applied resolution.
