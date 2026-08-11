# Sources & Attribution

All Quran data in this project is sourced from [Tanzil.net](https://tanzil.net). Tanzil is a well-known, long-standing project that distributes the Quran text and translations in machine-readable form.

## Files fetched

| file                 | URL                                                     | method | size    | purpose                                                    |
| -------------------- | ------------------------------------------------------- | ------ | ------- | ---------------------------------------------------------- |
| Metadata             | `https://tanzil.net/res/text/metadata/quran-data.xml`   | GET    | ~77 KB  | Surahs, juzs, hizb quarters, manzils, rukus, pages, sajdas |
| Quran text (Uthmani) | `https://tanzil.net/pub/download/index.php` (form POST) | POST   | ~1.3 MB | Per-ayah Arabic Uthmani text                               |

The Tanzil Quran text page is a form-based downloader, so the text file is fetched via a `POST` to `/pub/download/index.php` with the following form body (see `config/settings.yaml` for the live config):

```txt
quranType=uthmani
outType=txt-2
marks=true
sajdah=true
tatweel=true
agree=true
```

You can change `quranType` to any of: `simple`, `simple-plain`, `simple-min`, `simple-clean`, `uthmani`, `uthmani-min`.

## License

The Tanzil Quran text and metadata are provided under the [Tanzil license](https://tanzil.net/docs/Text_License). In short:

> Permission is granted to copy and distribute verbatim copies of the Quran text provided here, but changing the text is not allowed. The text can be used in any website or application, provided that its source (Tanzil Project) is clearly indicated, and a link is made to tanzil.net to enable users to keep track of changes.

The downloaded file in `raw/` is kept untouched. The public `text_raw` field contains the same text after Unicode normalization to the configured form (NFC by default); the analytical `text` and `text_clean` fields apply the documented mark, Bismillah, and diacritic transformations. Source URLs, request fingerprints, and downloaded-file SHA-256 hashes are recorded in the dataset metadata.

## Translations

Not included. Tanzil hosts ~100 translations across many languages at `https://tanzil.net/trans/`. To add translations to this project in the future, you would:

1. Add a `translations` block to `config/settings.yaml` listing the desired translation codes (e.g. `en.sahih`, `ar.jalalayn`).
2. Extend `src/quran_etl/download.py` to fetch them via POST.
3. Extend `src/quran_etl/transform.py` to attach translation text to each `Ayah`.
4. Extend `src/quran_etl/emit.py` to include `translations` in the per-ayah objects and in `quran.full.json`.

## Credits

- **Tanzil Project** — for the canonical Quran text and metadata. Visit [tanzil.net](https://tanzil.net).
