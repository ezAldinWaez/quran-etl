from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from quran_etl import cli

from .support import make_settings


def test_skip_emit_verify_is_rejected():
    with pytest.raises(SystemExit):
        cli.main(["--skip-emit", "--verify"])


@pytest.mark.parametrize(
    "flags",
    [
        ["--force-download", "--skip-download"],
        ["--min", "--min-only"],
        ["--schemas-only", "--verify"],
        ["--skip-emit", "--clean"],
    ],
)
def test_contradictory_flag_combinations_are_rejected(flags):
    with pytest.raises(SystemExit):
        cli.main(flags)


@pytest.mark.parametrize(
    ("flags", "expected"),
    [
        (["--verify"], ["emit-full", "verify-full"]),
        (["--min", "--verify"], ["emit-full", "emit-min", "verify-full", "verify-min"]),
        (["--min-only", "--verify"], ["emit-min", "verify-min"]),
    ],
)
def test_verify_targets_follow_emit_selection(tmp_path: Path, monkeypatch, flags, expected):
    settings = make_settings(tmp_path)
    settings.raw_dir.mkdir()
    (settings.raw_dir / "quran-data.xml").write_text("x", encoding="utf-8")
    (settings.raw_dir / "quran-uthmani.txt").write_text("x", encoding="utf-8")
    calls = []
    monkeypatch.setattr(cli.Settings, "load", classmethod(lambda cls, path: settings))
    monkeypatch.setattr(cli, "parse_metadata", lambda path: {})
    monkeypatch.setattr(cli, "parse_quran_text", lambda path: {})
    monkeypatch.setattr(cli, "build_graph", lambda metadata, verses, value: {})
    monkeypatch.setattr(cli, "source_provenance", lambda *args, **kwargs: {})
    def fake_emit(graph, value, *, include_full, include_minified):
        if include_full:
            calls.append("emit-full")
        if include_minified:
            calls.append("emit-min")
        return {}

    monkeypatch.setattr(cli, "emit", fake_emit)
    monkeypatch.setattr(cli, "emit_schemas", lambda path: {})
    monkeypatch.setattr(cli, "verify_full", lambda root, value: calls.append("verify-full") or [])
    monkeypatch.setattr(cli, "verify_min", lambda root, value: calls.append("verify-min") or [])
    assert cli.main(["--skip-download", *flags]) == 0
    assert calls == expected


def test_schemas_only_short_circuits_pipeline(tmp_path: Path, monkeypatch):
    settings = make_settings(tmp_path)
    calls = []
    monkeypatch.setattr(cli.Settings, "load", classmethod(lambda cls, path: settings))
    monkeypatch.setattr(cli, "emit_schemas", lambda path: calls.append(path) or {})
    assert cli.main(["--schemas-only"]) == 0
    assert calls == [Path("docs/json-schema")]


def test_render_delegates_to_qmd2word_api(monkeypatch, capsys):
    requests = []

    class RenderRequest:
        def __init__(self, *, entry_qmd, output):
            self.entry_qmd = entry_qmd
            self.output = output

    def render(request):
        requests.append(request)
        return SimpleNamespace(
            entry_qmd=request.entry_qmd,
            output=request.output,
            source_map={"blocks": [{}, {}]},
        )

    api = SimpleNamespace(RenderRequest=RenderRequest, render=render)
    monkeypatch.setattr(cli, "_load_qmd2word", lambda: api)

    assert cli.main(["render", "reports/tests/smoke.qmd", "--output", "smoke.docx"]) == 0
    assert requests[0].entry_qmd == Path("reports/tests/smoke.qmd")
    assert requests[0].output == Path("smoke.docx")
    assert '"anchored_blocks": 2' in capsys.readouterr().out


def test_compare_delegates_to_qmd2word_api(monkeypatch, capsys):
    requests = []

    class CompareRequest:
        def __init__(self, *, entry_qmd, edited_docx, output_dir):
            self.entry_qmd = entry_qmd
            self.edited_docx = edited_docx
            self.output_dir = output_dir

    def compare(request):
        requests.append(request)
        return SimpleNamespace(
            output_dir=request.output_dir,
            manifest=request.output_dir / "manifest.json",
            diff=request.output_dir / "diff.json",
            report=request.output_dir / "report.html",
            change_count=3,
        )

    api = SimpleNamespace(CompareRequest=CompareRequest, compare=compare)
    monkeypatch.setattr(cli, "_load_qmd2word", lambda: api)

    assert cli.main(
        [
            "compare",
            "reports/tests/smoke.qmd",
            "edited.docx",
            "--output-dir",
            "comparison",
        ]
    ) == 0
    assert requests[0].entry_qmd == Path("reports/tests/smoke.qmd")
    assert requests[0].edited_docx == Path("edited.docx")
    assert requests[0].output_dir == Path("comparison")
    assert '"change_count": 3' in capsys.readouterr().out


def test_report_command_explains_missing_qmd2word(monkeypatch, capsys):
    missing = ModuleNotFoundError("No module named 'qmd2word'", name="qmd2word")
    monkeypatch.setattr(cli, "_load_qmd2word", lambda: (_ for _ in ()).throw(missing))

    assert cli.main(["render", "report.qmd", "--output", "report.docx"]) == 1
    assert ".[reports]" in capsys.readouterr().err
