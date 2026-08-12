# quran-etl

An Arabic Quran dataset generator for analytics, applications, and LLM workflows—sourced from [Tanzil.net](https://tanzil.net), organized as JSON, and verified end to end.

**6,236 ayahs · 9 scopes · full and token-minimized editions · self-contained files**

[Download](https://github.com/ezAldinWaez/quran-etl/releases/latest) · [Data guide](data/README.md) · [Schema](docs/SCHEMA.md) · [Sources](docs/SOURCES.md) · [Reports](reports/README.md)

## Downloads

| Dataset | Best for |
|---|---|
| [`quran-data.zip`](https://github.com/ezAldinWaez/quran-etl/releases/latest/download/quran-data.zip) | Paired readable and token-minimized JSON |
| [DOCX and PDF reports](https://github.com/ezAldinWaez/quran-etl/releases/latest) | Editable and print-ready publications |

## What it provides

- Paired full and `.min.json` files in one documented [`data/`](data/README.md) tree.
- Self-contained range files with Quran ayahs embedded directly for simple analysis and consumption.
- Stable identifiers, relationships, provenance, and generated [JSON Schemas](docs/json-schema/).
- Strict verification of counts, coverage, partitions, references, text normalization, and output shape.

| Scope | Count | Scope | Count | Scope | Count |
|---|---:|---|---:|---|---:|
| Surah | 114 | Ayah | 6,236 | Juz | 30 |
| Manzil | 7 | Hizb | 60 | Rub | 240 |
| Ruku | 556 | Page | 604 | Sajdah | 15 |

## Build

Python 3.11 or newer is required.

```bash
python -m pip install -e ".[dev]"
python -m quran_etl --min --clean --verify
```

Use `python -m quran_etl --help` for all CLI options. Pipeline settings live in [`config/settings.yaml`](config/settings.yaml).

## Reports

The [`reports/`](reports/README.md) project turns the verified data into editable Arabic DOCX reports and PDF publications. Install the private report integration with `python -m pip install -e ".[reports]"`, then use `python -m quran_etl render` and `python -m quran_etl compare`; see the report guide for the complete workflow.

## License

The pipeline code is MIT-licensed. Quran text is provided by the [Tanzil Project](https://tanzil.net) under its own terms; see [Sources and attribution](docs/SOURCES.md).
