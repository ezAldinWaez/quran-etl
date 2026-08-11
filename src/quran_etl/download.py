"""HTTP downloader with on-disk caching and retries."""

from __future__ import annotations

import hashlib
import json
import logging
import time
from pathlib import Path

import requests

from .config import Settings
from .io_utils import atomic_write_bytes, atomic_write_text

logger = logging.getLogger(__name__)


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def request_fingerprint(
    method: str,
    url: str,
    form: dict[str, str] | None = None,
) -> str:
    payload = {
        "method": method.upper(),
        "url": url,
        "form": dict(sorted((form or {}).items())),
    }
    canonical = json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    return _sha256(canonical.encode("utf-8"))


def source_provenance(
    path: Path,
    *,
    method: str,
    url: str,
    form: dict[str, str] | None = None,
) -> dict[str, object]:
    return {
        "url": url,
        "method": method.upper(),
        "form": dict(sorted((form or {}).items())),
        "request_sha256": request_fingerprint(method, url, form),
        "content_sha256": _sha256(path.read_bytes()),
    }


def fetch(
    settings: Settings,
    path: str | None = None,
    *,
    url: str | None = None,
    method: str = "GET",
    form: dict[str, str] | None = None,
    force: bool = False,
    target_name: str | None = None,
) -> Path:
    """Download a Tanzil resource and return its cached path.

    The file is stored under `raw_dir` keyed by an SHA256 of the final URL
    (or the form payload, if POSTing). If the file already exists and
    `force` is False, it is reused.
    """
    if url is None:
        if path is None:
            raise ValueError("either path or url must be provided")
        url = f"{settings.base_url}{path}"

    method = method.upper()
    cache_key = request_fingerprint(method, url, form)
    target_dir = settings.raw_dir
    target_dir.mkdir(parents=True, exist_ok=True)
    cached = target_dir / (target_name or f"{cache_key}.bin")
    metadata_path = cached.with_suffix(cached.suffix + ".cache.json")

    if cached.exists() and not force:
        try:
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            metadata = {}
        if metadata.get("request_sha256") == cache_key:
            logger.debug("cache hit: %s -> %s", method, url, cached)
            return cached
        logger.info("cache fingerprint changed or missing for %s", cached.name)

    logger.info("%s %s", method, url)
    last_exc: Exception | None = None
    for attempt in range(1, settings.max_retries + 1):
        try:
            resp = requests.request(
                method,
                url,
                data=form,
                headers={"User-Agent": settings.user_agent},
                timeout=settings.timeout_seconds,
            )
            resp.raise_for_status()
            data = resp.content
            atomic_write_bytes(cached, data)
            atomic_write_text(
                metadata_path,
                json.dumps(
                    {
                        "request_sha256": cache_key,
                        "content_sha256": _sha256(data),
                        "url": url,
                        "method": method,
                        "form": dict(sorted((form or {}).items())),
                    },
                    ensure_ascii=False,
                    indent=2,
                    sort_keys=True,
                ) + "\n",
            )
            logger.info("saved %s (%d bytes, sha256=%s)", cached.name, len(data), _sha256(data)[:12])
            return cached
        except requests.RequestException as exc:
            last_exc = exc
            backoff = settings.backoff_factor * (2 ** (attempt - 1))
            logger.warning(
                "attempt %d/%d failed for %s %s: %s (retry in %.1fs)",
                attempt,
                settings.max_retries,
                method,
                url,
                exc,
                backoff,
            )
            if attempt < settings.max_retries:
                time.sleep(backoff)
    raise RuntimeError(f"failed to download {method} {url} after {settings.max_retries} attempts: {last_exc}")
