# Quranic Arabic Corpus morphology

This directory contains the Quranic Arabic Corpus morphology dataset used by reports that need word-level morphological segmentation. The current consumer is `reports/production/03-quran-orthography.qmd`, which extracts only the morphological distinctions needed for classifying hamza positions.

- Source: https://corpus.quran.com/download/
- Version: 0.4
- Copyright: Kais Dukes, 2011
- License: GNU General Public License

The dataset file retains its original copyright and terms-of-use headers. It is stored with Git LFS; run `git lfs pull` after cloning to materialize the full dataset before rendering the report.
