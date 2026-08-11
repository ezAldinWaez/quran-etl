from __future__ import annotations

import json
from pathlib import Path

from quran_etl.download import fetch, request_fingerprint

from .support import make_settings


class _Response:
    content = b"payload"

    def raise_for_status(self) -> None:
        return None


def test_request_fingerprint_is_stable_for_form_order():
    first = request_fingerprint("POST", "https://example.test", {"b": "2", "a": "1"})
    second = request_fingerprint("post", "https://example.test", {"a": "1", "b": "2"})
    assert first == second


def test_named_cache_is_reused_only_for_matching_fingerprint(tmp_path: Path, monkeypatch):
    settings = make_settings(tmp_path)
    calls = []

    def request(*args, **kwargs):
        calls.append((args, kwargs))
        return _Response()

    monkeypatch.setattr("quran_etl.download.requests.request", request)
    first = fetch(
        settings,
        url="https://example.test/text",
        method="POST",
        form={"a": "1"},
        target_name="text.txt",
    )
    second = fetch(
        settings,
        url="https://example.test/text",
        method="POST",
        form={"a": "1"},
        target_name="text.txt",
    )
    fetch(
        settings,
        url="https://example.test/text",
        method="POST",
        form={"a": "2"},
        target_name="text.txt",
    )
    assert first == second
    assert len(calls) == 2
    metadata = json.loads((settings.raw_dir / "text.txt.cache.json").read_text(encoding="utf-8"))
    assert metadata["form"] == {"a": "2"}
    assert metadata["content_sha256"]
