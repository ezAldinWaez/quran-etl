from __future__ import annotations

import logging
import os
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)


def _strict_bool(value: Any, name: str, default: bool) -> bool:
    if value is None:
        return default
    if not isinstance(value, bool):
        raise ValueError(f"{name} must be a YAML boolean")
    return value


def _nonempty_string(value: Any, name: str, default: str) -> str:
    if value is None:
        return default
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    return value.strip()


def _bounded_int(value: Any, name: str, default: int, *, minimum: int) -> int:
    if value is None:
        return default
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise ValueError(f"{name} must be an integer >= {minimum}")
    return value


def _nonnegative_float(value: Any, name: str, default: float) -> float:
    if value is None:
        return default
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value < 0:
        raise ValueError(f"{name} must be a number >= 0")
    return float(value)


@dataclass(frozen=True)
class Settings:
    base_url: str
    user_agent: str
    timeout_seconds: int
    max_retries: int
    backoff_factor: float
    metadata_path: str
    quran_text_post_url: str
    quran_text_form: dict[str, str]
    data_dir: Path
    raw_dir: Path
    indent: int
    ensure_ascii: bool
    text_type: str
    strip_bismillah_from_non_fatiha: bool
    bismillah_exempt_surahs: list[int]
    normal_form: str
    log_level: str

    @classmethod
    def load(cls, path: str | Path | None = None) -> Settings:
        path = Path(path) if path else Path("config/settings.yaml")
        if not path.exists():
            raise FileNotFoundError(f"Settings file not found: {path}")
        with path.open("r", encoding="utf-8") as f:
            raw = yaml.safe_load(f)
        if not isinstance(raw, dict):
            raise ValueError("settings root must be a mapping")
        dl = raw.get("download", {})
        src = raw.get("sources", {})
        out = raw.get("output", {})
        text = raw.get("text", {})
        log = raw.get("logging", {})
        sections = {
            "download": dl,
            "sources": src,
            "output": out,
            "text": text,
            "logging": log,
        }
        for name, section in sections.items():
            if not isinstance(section, dict):
                raise ValueError(f"{name} must be a mapping")
        base_url = _nonempty_string(
            dl.get("base_url"), "download.base_url", "https://tanzil.net"
        )
        user_agent = _nonempty_string(
            dl.get("user_agent"), "download.user_agent", "quran-etl/0.2"
        )
        form = src.get("quran_text_form", {
            "quranType": "uthmani", "outType": "txt-2",
            "marks": "true", "sajdah": "true", "tatweel": "true", "agree": "true",
        })
        exemptions = text.get("bismillah_exempt_surahs", [1, 9, 96])
        metadata_path = _nonempty_string(
            src.get("metadata_path"),
            "sources.metadata_path",
            "/res/text/metadata/quran-data.xml",
        )
        quran_text_post_url = _nonempty_string(
            src.get("quran_text_post_url"),
            "sources.quran_text_post_url",
            "/pub/download/index.php",
        )
        data_dir = _nonempty_string(out.get("data_dir"), "output.data_dir", "data")
        raw_dir = _nonempty_string(out.get("raw_dir"), "output.raw_dir", "raw")
        text_type = _nonempty_string(text.get("type"), "text.type", "uthmani")
        normal_form = _nonempty_string(text.get("normal_form"), "text.normal_form", "NFC")
        log_level = _nonempty_string(log.get("level"), "logging.level", "INFO")
        if not isinstance(form, dict) or not all(
            isinstance(k, str) and isinstance(v, str) for k, v in form.items()
        ):
            raise ValueError("sources.quran_text_form must map strings to strings")
        if not isinstance(exemptions, list) or any(
            isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= 114
            for value in exemptions
        ):
            raise ValueError("text.bismillah_exempt_surahs must contain surah numbers 1..114")
        if len(set(exemptions)) != len(exemptions):
            raise ValueError("text.bismillah_exempt_surahs must not contain duplicates")
        if normal_form not in {"NFC", "NFD", "NFKC", "NFKD"}:
            raise ValueError("text.normal_form must be NFC, NFD, NFKC, or NFKD")
        unicodedata.normalize(normal_form, "")
        if not isinstance(log_level, str) or log_level.upper() not in logging.getLevelNamesMapping():
            raise ValueError("logging.level must be a recognized logging level")
        return cls(
            base_url=base_url.rstrip("/"),
            user_agent=user_agent,
            timeout_seconds=_bounded_int(
                dl.get("timeout_seconds"), "download.timeout_seconds", 30, minimum=1
            ),
            max_retries=_bounded_int(
                dl.get("max_retries"), "download.max_retries", 3, minimum=1
            ),
            backoff_factor=_nonnegative_float(
                dl.get("backoff_factor"), "download.backoff_factor", 0.5
            ),
            metadata_path=metadata_path,
            quran_text_post_url=quran_text_post_url,
            quran_text_form=dict(form),
            data_dir=Path(data_dir),
            raw_dir=Path(raw_dir),
            indent=_bounded_int(out.get("indent"), "output.indent", 2, minimum=0),
            ensure_ascii=_strict_bool(out.get("ensure_ascii"), "output.ensure_ascii", False),
            text_type=text_type,
            strip_bismillah_from_non_fatiha=_strict_bool(
                text.get("strip_bismillah_from_non_fatiha"),
                "text.strip_bismillah_from_non_fatiha",
                True,
            ),
            bismillah_exempt_surahs=list(exemptions),
            normal_form=normal_form,
            log_level=log_level.upper(),
        )

    def configure_logging(self) -> None:
        level = os.environ.get("QURAN_ETL_LOG", self.log_level).upper()
        logging.basicConfig(
            level=level,
            format="%(asctime)s %(levelname)s %(name)s :: %(message)s",
            datefmt="%H:%M:%S",
        )
