"""CLI entrypoint: `python -m quran_etl` or `quran-etl`."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path
from types import ModuleType

from .config import Settings
from .download import fetch, source_provenance
from .emit import emit
from .parse import parse_metadata, parse_quran_text
from .schemas_emit import emit as emit_schemas
from .transform import build_graph
from .verify import verify_full, verify_min

logger = logging.getLogger(__name__)

REPORT_COMMANDS = frozenset({"render", "compare"})


def _purge_json_files(root: Path, *, minified: bool | None = None) -> None:
    """Delete selected `*.json` files under `root`, recursively.

    `minified=True` selects `.min.json`, `False` selects full JSON,
    and `None` selects both variants. Markdown and other files survive.
    """
    if not root.exists():
        return
    for path in root.rglob("*"):
        is_json = path.is_file() and path.suffix.lower() == ".json"
        is_minified = path.name.endswith(".min.json")
        if is_json and (minified is None or is_minified == minified):
            try:
                path.unlink()
            except OSError as exc:
                logger.warning("could not remove %s: %s", path, exc)
    # Remove now-empty directories, deepest first
    all_paths = [p for p in root.rglob("*") if p.is_dir()]
    all_paths.sort(key=lambda p: len(p.parts), reverse=True)
    for path in all_paths:
        try:
            path.rmdir()
        except OSError:
            pass  # not empty (e.g. has a README) or not removable
    # And root itself if it became empty
    try:
        root.rmdir()
    except OSError:
        pass


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="quran-etl",
        description="Build an LLM-friendly JSON Quran dataset from Tanzil.net.",
        epilog=(
            "Report commands: quran-etl render <entry.qmd> --output <file.docx>; "
            "quran-etl compare <entry.qmd> <edited.docx> --output-dir <directory>"
        ),
    )
    p.add_argument("--config", default="config/settings.yaml", help="Path to YAML settings.")
    download = p.add_mutually_exclusive_group()
    download.add_argument("--force-download", action="store_true", help="Re-fetch raw files even if cached.")
    download.add_argument("--skip-download", action="store_true", help="Use cached raw files only.")
    p.add_argument("--skip-emit", action="store_true", help="Stop after building the graph in memory.")
    p.add_argument(
        "--verify",
        action="store_true",
        help="After emit, re-walk data/ and check invariants (counts, refs).",
    )
    p.add_argument(
        "--schemas-only",
        action="store_true",
        help="Only (re)write JSON Schema files; do not download or transform.",
    )
    variants = p.add_mutually_exclusive_group()
    variants.add_argument(
        "--min",
        dest="emit_min",
        action="store_true",
        help="Also emit paired *.min.json files under <data_dir>/.",
    )
    variants.add_argument(
        "--min-only",
        action="store_true",
        help="Only emit paired *.min.json files; leave full files unchanged.",
    )
    p.add_argument(
        "--clean",
        action="store_true",
        help="Before emitting, delete selected generated JSON under data/ "
             "while preserving READMEs and the unselected variant.",
    )
    return p


def _build_report_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="quran-etl",
        description="Render and compare Quran ETL reports with qmd2word.",
    )
    commands = parser.add_subparsers(dest="report_command", required=True)
    render_parser = commands.add_parser("render", help="Render one Quarto entry QMD to DOCX.")
    render_parser.add_argument("entry_qmd", type=Path)
    render_parser.add_argument("--output", type=Path, required=True)
    compare_parser = commands.add_parser(
        "compare",
        help="Render a QMD baseline and compare it with an edited DOCX.",
    )
    compare_parser.add_argument("entry_qmd", type=Path)
    compare_parser.add_argument("edited_docx", type=Path)
    compare_parser.add_argument("--output-dir", type=Path, required=True)
    return parser


def _load_qmd2word() -> ModuleType:
    import qmd2word

    return qmd2word


def _run_report_command(argv: list[str]) -> int:
    args = _build_report_parser().parse_args(argv)
    try:
        qmd2word = _load_qmd2word()
    except ModuleNotFoundError as exc:
        if exc.name != "qmd2word":
            raise
        print(
            "quran-etl: report commands require qmd2word; "
            'install it with `python -m pip install -e ".[reports]"`.',
            file=sys.stderr,
        )
        return 1

    try:
        if args.report_command == "render":
            result = qmd2word.render(
                qmd2word.RenderRequest(entry_qmd=args.entry_qmd, output=args.output)
            )
            payload = {
                "entry_qmd": str(result.entry_qmd),
                "output": str(result.output),
                "anchored_blocks": len(result.source_map.get("blocks", [])),
            }
        else:
            result = qmd2word.compare(
                qmd2word.CompareRequest(
                    entry_qmd=args.entry_qmd,
                    edited_docx=args.edited_docx,
                    output_dir=args.output_dir,
                )
            )
            payload = {
                "output_dir": str(result.output_dir),
                "manifest": str(result.manifest),
                "diff": str(result.diff),
                "report": str(result.report),
                "change_count": result.change_count,
            }
    except Exception as exc:
        print(f"quran-etl {args.report_command}: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(payload, ensure_ascii=False))
    return 0


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] in REPORT_COMMANDS:
        return _run_report_command(argv)
    parser = _build_parser()
    args = parser.parse_args(argv)
    if args.skip_emit and (args.verify or args.emit_min or args.min_only or args.clean):
        parser.error("--skip-emit cannot be combined with emit, clean, or verify flags")
    if args.schemas_only and any(
        (
            args.force_download,
            args.skip_download,
            args.skip_emit,
            args.verify,
            args.emit_min,
            args.min_only,
            args.clean,
        )
    ):
        parser.error("--schemas-only cannot be combined with pipeline flags")
    settings = Settings.load(args.config)
    settings.configure_logging()

    if args.schemas_only:
        emit_schemas(Path("docs/json-schema"))
        return 0

    # Resolve raw sources
    if not args.skip_download:
        meta = fetch(settings, path=settings.metadata_path,
                     target_name="quran-data.xml", force=args.force_download)
        text = fetch(settings, path=settings.quran_text_post_url,
                     method="POST", form=settings.quran_text_form,
                     target_name=f"quran-{settings.text_type}.txt",
                     force=args.force_download)
    else:
        meta = settings.raw_dir / "quran-data.xml"
        text = settings.raw_dir / f"quran-{settings.text_type}.txt"
        if not meta.exists() or not text.exists():
            logger.error("cache miss: %s or %s missing", meta, text)
            return 2

    metadata = parse_metadata(meta)
    verses = parse_quran_text(text)
    graph = build_graph(metadata, verses, settings)
    metadata_url = f"{settings.base_url}{settings.metadata_path}"
    text_url = f"{settings.base_url}{settings.quran_text_post_url}"
    graph["provenance"] = {
        "metadata": source_provenance(meta, method="GET", url=metadata_url),
        "text": source_provenance(
            text,
            method="POST",
            url=text_url,
            form=settings.quran_text_form,
        ),
    }

    if args.skip_emit:
        logger.info("skip-emit: graph has %d ayahs, %d surahs",
                    len(graph["ayahs"]), len(graph["surahs"]))
        return 0

    include_full = not args.min_only
    include_minified = args.emit_min or args.min_only
    if args.clean:
        selected_variant = None
        if not include_minified:
            selected_variant = False
        elif not include_full:
            selected_variant = True
        logger.info("purging selected JSON under %s", settings.data_dir)
        _purge_json_files(settings.data_dir, minified=selected_variant)
    manifests = emit(
        graph,
        settings,
        include_full=include_full,
        include_minified=include_minified,
    )
    if include_full:
        emit_schemas(Path("docs/json-schema"))
    for variant, manifest in manifests.items():
        for key, path in manifest.items():
            logger.info("wrote %s %s -> %s", variant, key, path)

    if args.verify:
        errors: list[str] = []
        if not args.min_only:
            errors.extend(verify_full(settings.data_dir, settings))
        if args.emit_min or args.min_only:
            errors.extend(verify_min(settings.data_dir, settings))
        if errors:
            logger.error("VERIFY FAILED with %d errors:", len(errors))
            for error in errors[:100]:
                logger.error("  - %s", error)
            return 1
        logger.info("VERIFY OK: all selected output invariants hold")
    return 0


if __name__ == "__main__":
    sys.exit(main())
