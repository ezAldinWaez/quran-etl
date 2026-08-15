---
name: docduet-sync
description: Reconcile an editor-returned DOCX into its corresponding Quarto QMD project with DocDuet compare. Use when Word is an editorial authority and an agent must interpret content, structure, styles, comments, tracked changes, fields, tables, images, or generated-output edits, update the right QMD/code/data/config sources, and verify convergence.
---

# Sync edited Word to QMD

Use the edited DOCX as editorial authority for its review round and the matching calling project as the executable representation. Synchronize them semantically; do not seek byte-identical OOXML or infer state from another project that also uses DocDuet.

## Preconditions

- Require the matching entry QMD/project/data/environment version for the returned DOCX. Stop if correspondence is materially uncertain.
- Preserve the returned editor DOCX exactly. Never modify, replace, accept revisions in, or overwrite it.
- Read [references/diff-contract.md](references/diff-contract.md) before interpreting comparison artifacts.

## Reconciliation loop

1. Select a fresh, caller-approved output directory and run:

   ```bash
   docduet compare path/to/originally-sent.docx path/to/editor-returned.docx \
     --output-dir path/to/fresh-comparison
   ```

   If the caller supplies an existing completed bundle, it may be used after verifying its manifest input hashes against the baseline and editor DOCX. Never reuse its directory for another comparison.

2. Read `manifest.json` and `diff.json`; read `source-context.json` when a QMD baseline produced it. Use `report.html` for navigation. Request or generate `--evidence full` only when an ambiguous change needs the documents or raw IR.
3. Each schema-2 change already groups related facets at one location. Anchors and locations aid alignment; they do not dictate source syntax. Interpret insertions, deletions, moves, replacements, structural changes, semantic formatting, comments, and revision evidence together.
   For an unanchored insertion, inspect the nearest anchored baseline/edited blocks, both Pandoc ASTs, and template-controlled boundaries. If placement remains ambiguous, defer and ask for editorial direction instead of appending it to a plausible-looking source location.
4. Translate each editorial change into suitable QMD semantics using judgment:
   - edit the relevant entry or included QMD for authored prose and structure;
   - edit code, data, configuration, bibliography, or resources when generated material was changed;
   - preserve computations rather than automatically freezing their current output into static content;
   - treat comments as instructions or discussion, not automatically as document text;
   - treat edited citations, cross-references, fields, tables, figures, captions, and executable output as intent that may require a non-prose source change.
   - distinguish semantic intent from redundant direct formatting. If Word adds bold to a heading whose named style is already bold, preserve the semantic outcome and record any representation-only residual rather than inventing redundant QMD markup.
5. Record every content or semantic-style change in `resolution.json` with its diff IDs, status, source files, rationale, and verification result. Use exactly one status:
   - `applied`: implemented and no longer appears after rerendering;
   - `intentionally-retained`: reviewed and intentionally kept as generated;
   - `deferred`: accepted intent but postponed with a concrete reason;
   - `unsupported`: cannot be represented safely, with evidence and alternatives.
6. Rerender to a new generated DOCX and run `docduet compare` again into another fresh directory. Never use the editor-returned DOCX path as render output.
7. Repeat until every applicable change disappears or has an explicit non-applied resolution. Confirm that no new unintended differences were introduced.
   A source change may eliminate the original diff while producing new normalization-only diff IDs. Link the old and new IDs in the same resolution and use `intentionally-retained` only after verifying semantic equivalence and documenting why the generated representation is authoritative.
8. Report changed sources, comparison directories, resolution counts, remaining decisions, and verification results.

## Boundaries

- `diff.json` is descriptive evidence, not a QMD patch or a source-level recommendation.
- Do not rewrite the QMD blindly from Word order or formatting; preserve valid executable and project semantics.
- Prefer the exact DOCX sent for review. Do not create a baseline registry, perform a source-control checkout, or implement a three-way merge inside DocDuet.
- Do not claim reconciliation success from DOCX binary equality. Success is semantic convergence plus complete resolution records.
