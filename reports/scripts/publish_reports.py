"""Build Quran data and reports, then publish the repository's sole release."""

from __future__ import annotations

import argparse
import json
import logging
import platform
import re
import subprocess
import sys
import zipfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import quote

import yaml

ROOT = Path(__file__).resolve().parents[2]
REPORTS_DIR = ROOT / "reports"
PRODUCTION_DIR = REPORTS_DIR / "production"
DOCX_DIR = REPORTS_DIR / "output" / "production"
PDF_DIR = REPORTS_DIR / "output" / "pdf"
RELEASE_DIR = REPORTS_DIR / "output" / "release"
LOGGER = logging.getLogger("publish-reports")
EXPECTED_DATASET_JSON_FILES = 15_746


@dataclass(frozen=True)
class Report:
    source: Path
    title: str
    subtitle: str

    @property
    def stem(self) -> str:
        return self.source.stem

    @property
    def docx(self) -> Path:
        return DOCX_DIR / f"{self.stem}.docx"

    @property
    def pdf(self) -> Path:
        return PDF_DIR / f"{self.stem}.pdf"


@dataclass(frozen=True)
class Dataset:
    root: Path
    title: str
    description: str
    archive_name: str

    @property
    def archive(self) -> Path:
        return RELEASE_DIR / self.archive_name

    @property
    def dataset_files(self) -> list[Path]:
        return sorted(
            path
            for path in self.root.rglob("*")
            if path.is_file() and (path.suffix == ".json" or path.name == "README.md")
        )

    @property
    def files(self) -> list[Path]:
        supporting_files = [
            ROOT / "docs" / "SCHEMA.md",
            ROOT / "docs" / "SOURCES.md",
            *(ROOT / "docs" / "json-schema").glob("*.json"),
        ]
        return sorted([*self.dataset_files, *supporting_files])

    @property
    def archive_entries(self) -> list[tuple[Path, str]]:
        entries = [(path, path.relative_to(ROOT).as_posix()) for path in self.files]
        entries.append((ROOT / "LICENSE", "LICENSE.txt"))
        return entries

    @property
    def json_file_count(self) -> int:
        return sum(path.suffix == ".json" for path in self.dataset_files)


def configure_logging(level: str) -> Path:
    RELEASE_DIR.mkdir(parents=True, exist_ok=True)
    log_path = RELEASE_DIR / "reports-release.log"
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s :: %(message)s")
    LOGGER.setLevel(level)
    LOGGER.handlers.clear()
    console = logging.StreamHandler()
    console.setFormatter(formatter)
    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setFormatter(formatter)
    LOGGER.addHandler(console)
    LOGGER.addHandler(file_handler)
    return log_path


def run(command: list[str], *, capture: bool = False) -> str:
    LOGGER.info("Running: %s", subprocess.list2cmdline(command))
    if capture:
        completed = subprocess.run(
            command,
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        if completed.stdout.strip():
            LOGGER.debug("stdout: %s", completed.stdout.strip())
        if completed.stderr.strip():
            LOGGER.debug("stderr: %s", completed.stderr.strip())
        if completed.returncode:
            raise RuntimeError(
                f"Command failed with exit code {completed.returncode}: "
                f"{subprocess.list2cmdline(command)}\n{completed.stderr.strip()}"
            )
        return completed.stdout.strip()

    process = subprocess.Popen(
        command,
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    assert process.stdout is not None
    for line in process.stdout:
        LOGGER.info("%s", line.rstrip())
    return_code = process.wait()
    if return_code:
        raise RuntimeError(
            f"Command failed with exit code {return_code}: "
            f"{subprocess.list2cmdline(command)}"
        )
    return ""


def read_front_matter(path: Path) -> dict[str, object]:
    text = path.read_text(encoding="utf-8")
    match = re.match(r"\A---\s*\n(.*?)\n---\s*(?:\n|\Z)", text, flags=re.DOTALL)
    if not match:
        raise ValueError(f"Missing YAML front matter: {path}")
    metadata = yaml.safe_load(match.group(1)) or {}
    if not isinstance(metadata, dict):
        raise ValueError(f"Invalid YAML front matter: {path}")
    return metadata


def discover_reports() -> list[Report]:
    reports = []
    for source in sorted(PRODUCTION_DIR.glob("*.qmd")):
        metadata = read_front_matter(source)
        title = str(metadata.get("title", "")).strip()
        if not title:
            raise ValueError(f"Report title is required: {source}")
        reports.append(
            Report(
                source=source,
                title=title,
                subtitle=str(metadata.get("subtitle", "")).strip(),
            )
        )
    if not reports:
        raise RuntimeError(f"No production reports found under {PRODUCTION_DIR}")
    LOGGER.info("Discovered %d production reports", len(reports))
    for report in reports:
        LOGGER.info("Report: %s (%s)", report.title, report.source.name)
    return reports


def verify_data() -> None:
    run([sys.executable, "-m", "quran_etl", "--min", "--verify"])


def discover_datasets() -> list[Dataset]:
    datasets = [
        Dataset(
            root=ROOT / "data",
            title="Paired Quran dataset",
            description="Readable full-key JSON paired with compact `.min.json` files in one documented tree.",
            archive_name="quran-data.zip",
        ),
    ]
    for dataset in datasets:
        if not dataset.root.is_dir():
            raise RuntimeError(f"Dataset directory does not exist: {dataset.root}")
        if dataset.json_file_count != EXPECTED_DATASET_JSON_FILES:
            raise RuntimeError(
                f"Expected {EXPECTED_DATASET_JSON_FILES:,} JSON files under "
                f"{dataset.root}, found {dataset.json_file_count:,}"
            )
        LOGGER.info(
            "Dataset: %s (%s; %d JSON files)",
            dataset.title,
            dataset.root.name,
            dataset.json_file_count,
        )
    return datasets


def validate_dataset_archive(dataset: Dataset) -> None:
    path = dataset.archive
    if not path.is_file() or path.stat().st_size == 0:
        raise RuntimeError(f"Dataset archive was not created: {path}")
    expected_names = {archive_name for _, archive_name in dataset.archive_entries}
    with zipfile.ZipFile(path) as archive:
        actual_names = set(archive.namelist())
        if actual_names != expected_names:
            raise RuntimeError(f"Dataset archive contents do not match {dataset.root}")
        corrupt_name = archive.testzip()
        if corrupt_name is not None:
            raise RuntimeError(f"Corrupt member in dataset archive: {corrupt_name}")


def build_dataset_archives(datasets: list[Dataset]) -> None:
    RELEASE_DIR.mkdir(parents=True, exist_ok=True)
    for dataset in datasets:
        LOGGER.info("Building dataset archive: %s", dataset.archive.name)
        temporary = dataset.archive.with_suffix(".zip.tmp")
        with zipfile.ZipFile(
            temporary, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9
        ) as archive:
            for path, archive_name in dataset.archive_entries:
                archive.write(path, archive_name)
        temporary.replace(dataset.archive)
        validate_dataset_archive(dataset)
        LOGGER.info(
            "Built dataset archive: %s (%.1f MiB)",
            dataset.archive,
            dataset.archive.stat().st_size / (1024 * 1024),
        )


def validate_docx(path: Path) -> None:
    if not path.is_file() or path.stat().st_size == 0:
        raise RuntimeError(f"DOCX was not created: {path}")
    if not zipfile.is_zipfile(path):
        raise RuntimeError(f"Invalid DOCX package: {path}")
    with zipfile.ZipFile(path) as package:
        if "[Content_Types].xml" not in package.namelist():
            raise RuntimeError(f"DOCX package is missing [Content_Types].xml: {path}")


def render_reports(reports: list[Report]) -> None:
    DOCX_DIR.mkdir(parents=True, exist_ok=True)
    for report in reports:
        LOGGER.info("Rendering %s", report.title)
        run(
            [
                sys.executable,
                "-m",
                "quran_etl",
                "render",
                str(report.source),
                "--output",
                str(report.docx),
            ]
        )
        validate_docx(report.docx)
        LOGGER.info("Rendered DOCX: %s", report.docx)


def update_story_fields(document: object) -> None:
    for story_type in range(1, 18):
        try:
            story = document.StoryRanges.Item(story_type)
        except Exception:
            continue
        while story is not None:
            try:
                story.Fields.Update()
                story = story.NextStoryRange
            except Exception:
                break


def validate_pdf(path: Path) -> None:
    if not path.is_file() or path.stat().st_size == 0:
        raise RuntimeError(f"PDF was not created: {path}")
    with path.open("rb") as pdf_file:
        header = pdf_file.read(5)
    if header != b"%PDF-":
        raise RuntimeError(f"Invalid PDF header: {path}")


def export_pdfs_with_word(reports: list[Report]) -> None:
    if platform.system() != "Windows":
        raise RuntimeError("Microsoft Word COM export requires Windows")
    try:
        import pythoncom
        from win32com.client import DispatchEx
    except ImportError as error:
        raise RuntimeError(
            "pywin32 is required; install reports/requirements.txt"
        ) from error

    PDF_DIR.mkdir(parents=True, exist_ok=True)
    pythoncom.CoInitialize()
    word = None
    try:
        LOGGER.info("Starting Microsoft Word COM automation")
        word = DispatchEx("Word.Application")
        word.Visible = False
        word.DisplayAlerts = 0
        word.ScreenUpdating = False
        word.AutomationSecurity = 3
        word.Options.SaveNormalPrompt = False
        word.Options.ConfirmConversions = False
        word.Options.UpdateLinksAtOpen = False
        for report in reports:
            validate_docx(report.docx)
            document = None
            try:
                LOGGER.info("Updating fields and exporting PDF: %s", report.title)
                document = word.Documents.Open(
                    str(report.docx.resolve()),
                    ConfirmConversions=False,
                    ReadOnly=False,
                    AddToRecentFiles=False,
                    Revert=False,
                    NoEncodingDialog=True,
                )
                document.Fields.Update()
                update_story_fields(document)
                for index in range(1, document.TablesOfContents.Count + 1):
                    document.TablesOfContents.Item(index).Update()
                document.Save()
                document.ExportAsFixedFormat(
                    OutputFileName=str(report.pdf.resolve()),
                    ExportFormat=17,
                    OpenAfterExport=False,
                    OptimizeFor=0,
                    Range=0,
                    Item=0,
                    IncludeDocProps=True,
                    KeepIRM=True,
                    CreateBookmarks=1,
                    DocStructureTags=True,
                    BitmapMissingFonts=True,
                    UseISO19005_1=False,
                )
                validate_pdf(report.pdf)
                LOGGER.info("Exported PDF: %s", report.pdf)
            finally:
                if document is not None:
                    try:
                        document.Close(SaveChanges=False)
                    except Exception:
                        LOGGER.warning("Word document was already unavailable")
    finally:
        if word is not None:
            try:
                word.Quit()
            except Exception:
                LOGGER.warning("Word application was already unavailable")
        pythoncom.CoUninitialize()
        LOGGER.info("Microsoft Word COM automation stopped")


def repository_slug() -> str:
    remote = run(["git", "remote", "get-url", "origin"], capture=True)
    match = re.search(r"github\.com(?::|/)([^/]+/[^/]+?)(?:\.git)?$", remote)
    if not match:
        raise RuntimeError(f"Cannot derive GitHub repository from origin: {remote}")
    return match.group(1)


def local_head() -> str:
    return run(["git", "rev-parse", "HEAD"], capture=True)


def publish_head(repository: str, default_branch: str) -> str:
    tracked_changes = run(
        ["git", "status", "--porcelain", "--untracked-files=no"], capture=True
    )
    if tracked_changes:
        raise RuntimeError("Commit tracked changes before publishing a release")
    head = local_head()
    remote_head = run(
        [
            "gh",
            "api",
            f"repos/{repository}/commits/{quote(default_branch, safe='')}",
            "--jq",
            ".sha",
        ],
        capture=True,
    )
    if head != remote_head:
        raise RuntimeError(
            f"Local HEAD {head} does not match origin/{default_branch} {remote_head}; "
            "push the exact commit before publishing"
        )
    return head


def move_release_tag(repository: str, tag: str, head: str) -> None:
    run(
        [
            "gh",
            "api",
            "--method",
            "PATCH",
            f"repos/{repository}/git/refs/tags/{quote(tag, safe='')}",
            "-f",
            f"sha={head}",
            "-F",
            "force=true",
        ]
    )
    resolved_head = run(
        [
            "gh",
            "api",
            f"repos/{repository}/commits/{quote(tag, safe='')}",
            "--jq",
            ".sha",
        ],
        capture=True,
    )
    if resolved_head != head:
        raise RuntimeError(
            f"Release tag {tag} resolves to {resolved_head}, expected {head}"
        )
    LOGGER.info("Release tag %s now points to %s", tag, head)


def release_notes(
    reports: list[Report],
    datasets: list[Dataset],
    repository: str,
    tag: str,
    head: str,
    generated_at: datetime,
) -> str:
    base_url = f"https://github.com/{repository}/releases/download/{quote(tag, safe='')}"
    lines = [
        "# Quran Data and Reports",
        "",
        "The latest verified Quran JSON datasets, editable Word reports, and print-ready PDFs generated directly from this repository.",
        "",
        "## Dataset index",
        "",
    ]
    for index, dataset in enumerate(datasets, 1):
        size_mib = dataset.archive.stat().st_size / (1024 * 1024)
        lines.append(f"{index}. **{dataset.title}**")
        lines.append(f"   - {dataset.description}")
        lines.append(
            f"   - Contents: `{dataset.root.name}/` with {dataset.json_file_count:,} dataset JSON files, plus schema, source-attribution, and license documentation."
        )
        lines.append(
            f"   - Download: [{dataset.archive.name}]({base_url}/{quote(dataset.archive.name)}) ({size_mib:.1f} MiB)"
        )
    lines.extend(("", "## Report index", ""))
    for index, report in enumerate(reports, 1):
        lines.append(f"{index}. **{report.title}**")
        if report.subtitle:
            lines.append(f"   - Subtitle: {report.subtitle}")
        lines.append(
            f"   - Downloads: [Word]({base_url}/{quote(report.docx.name)}) | [PDF]({base_url}/{quote(report.pdf.name)})"
        )
    lines.extend(
        (
            "",
            f"Source revision: [`{head[:7]}`](https://github.com/{repository}/commit/{head})",
            "",
            f"Generated automatically from verified ETL data and `reports/production/` on {generated_at.astimezone(UTC).strftime('%Y-%m-%d %H:%M UTC')}.",
        )
    )
    return "\n".join(lines) + "\n"


def gh_json(arguments: list[str]) -> object:
    output = run(["gh", *arguments], capture=True)
    return json.loads(output)


def publish_release(
    reports: list[Report], datasets: list[Dataset], default_tag: str, title: str
) -> tuple[str, str]:
    run(["gh", "auth", "status"])
    repository_info = gh_json(
        ["repo", "view", "--json", "nameWithOwner,defaultBranchRef"]
    )
    if not isinstance(repository_info, dict):
        raise RuntimeError("Unexpected response from gh repo view")
    repository = str(repository_info["nameWithOwner"])
    default_branch = str(repository_info["defaultBranchRef"]["name"])
    head = publish_head(repository, default_branch)
    releases = gh_json(
        [
            "release",
            "list",
            "--limit",
            "100",
            "--json",
            "tagName,name,isDraft,isPrerelease,publishedAt",
        ]
    )
    if not isinstance(releases, list):
        raise RuntimeError("Unexpected response from gh release list")
    if len(releases) > 1:
        tags = ", ".join(str(release["tagName"]) for release in releases)
        raise RuntimeError(
            f"Expected at most one GitHub release, found {len(releases)}: {tags}"
        )
    tag = str(releases[0]["tagName"]) if releases else default_tag
    notes_path = RELEASE_DIR / "release-notes.md"
    notes_path.write_text(
        release_notes(reports, datasets, repository, tag, head, datetime.now(UTC)),
        encoding="utf-8",
    )
    dataset_assets = [dataset.archive for dataset in datasets]
    report_assets = [path for report in reports for path in (report.docx, report.pdf)]
    assets = [*dataset_assets, *report_assets]
    for asset in assets:
        if asset.suffix == ".docx":
            validate_docx(asset)
        elif asset.suffix == ".pdf":
            validate_pdf(asset)
    for dataset in datasets:
        validate_dataset_archive(dataset)

    if releases:
        LOGGER.info("Updating the sole GitHub release: %s", tag)
        run(
            [
                "gh",
                "release",
                "edit",
                tag,
                "--title",
                title,
                "--notes-file",
                str(notes_path),
            ]
        )
        move_release_tag(repository, tag, head)
    else:
        LOGGER.info("Creating the sole GitHub release: %s", tag)
        run(
            [
                "gh",
                "release",
                "create",
                tag,
                "--title",
                title,
                "--notes-file",
                str(notes_path),
                "--target",
                head,
            ]
        )
        resolved_head = run(
            [
                "gh",
                "api",
                f"repos/{repository}/commits/{quote(tag, safe='')}",
                "--jq",
                ".sha",
            ],
            capture=True,
        )
        if resolved_head != head:
            raise RuntimeError(
                f"Release tag {tag} resolves to {resolved_head}, expected {head}"
            )
    run(["gh", "release", "upload", tag, *map(str, dataset_assets), "--clobber"])
    run(["gh", "release", "upload", tag, *map(str, report_assets), "--clobber"])
    release_details = gh_json(["api", f"repos/{repository}/releases/tags/{tag}"])
    desired_names = {asset.name for asset in assets}
    for asset in release_details.get("assets", []):
        if asset["name"] not in desired_names:
            LOGGER.info("Removing stale release asset: %s", asset["name"])
            run(
                [
                    "gh",
                    "api",
                    "--method",
                    "DELETE",
                    f"repos/{repository}/releases/assets/{asset['id']}",
                ]
            )
    url = run(["gh", "release", "view", tag, "--json", "url", "--jq", ".url"], capture=True)
    return tag, url


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build Quran datasets and production reports, then publish the repository's sole GitHub release."
    )
    parser.add_argument(
        "--skip-data",
        action="store_true",
        help="Use the existing paired data tree without rebuilding or semantic verification",
    )
    parser.add_argument("--skip-render", action="store_true", help="Use existing DOCX files")
    parser.add_argument("--skip-pdf", action="store_true", help="Use existing PDFs and do not start Word")
    parser.add_argument("--skip-publish", action="store_true", help="Do not change GitHub")
    parser.add_argument("--release-tag", default="latest", help="Tag used when no release exists")
    parser.add_argument(
        "--release-title", default="Quran Data and Reports", help="GitHub release title"
    )
    parser.add_argument(
        "--log-level",
        choices=("DEBUG", "INFO", "WARNING", "ERROR"),
        default="INFO",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    log_path = configure_logging(args.log_level)
    try:
        LOGGER.info("Starting Quran data and report release workflow")
        reports = discover_reports()
        if not args.skip_data:
            verify_data()
        datasets = discover_datasets()
        build_dataset_archives(datasets)
        if not args.skip_render:
            render_reports(reports)
        else:
            for report in reports:
                validate_docx(report.docx)
        if not args.skip_pdf:
            export_pdfs_with_word(reports)
        else:
            for report in reports:
                validate_pdf(report.pdf)
        if args.skip_publish:
            repository = repository_slug()
            notes_path = RELEASE_DIR / "release-notes.md"
            notes_path.write_text(
                release_notes(
                    reports,
                    datasets,
                    repository,
                    args.release_tag,
                    local_head(),
                    datetime.now(UTC),
                ),
                encoding="utf-8",
            )
            LOGGER.info("Skipped GitHub publication; generated notes at %s", notes_path)
        else:
            tag, url = publish_release(
                reports, datasets, args.release_tag, args.release_title
            )
            LOGGER.info("Published release %s: %s", tag, url)
        LOGGER.info("Workflow completed successfully; log: %s", log_path)
        return 0
    except Exception:
        LOGGER.exception("Workflow failed; log: %s", log_path)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
