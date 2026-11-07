"""Shared helpers for the Quran data pipeline (stdlib only).

Network calls send a browser-like User-Agent: QuranEnc answers some default
Python user agents with HTTP 403.
"""

from __future__ import annotations

import gzip
import hashlib
import io
import json
import time
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
QURAN_DIR = REPO_ROOT / "quran" / "v1"
TRANSLATIONS_DIR = QURAN_DIR / "translations"
CACHE_DIR = REPO_ROOT / "build" / "quran_raw"
CONFIG_PATH = Path(__file__).resolve().parent / "translations.json"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/130.0 Safari/537.36 seccadem-data/1.0"
)

SURAH_COUNT = 114
AYAH_COUNT = 6236
PAGE_COUNT = 604
JUZ_COUNT = 30


def fetch(url: str, *, retries: int = 4, timeout: int = 60) -> bytes:
    last: Exception | None = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read()
        except Exception as exc:  # noqa: BLE001 - retried, then re-raised
            last = exc
            time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"GET {url} failed: {last}")


def fetch_json(url: str) -> dict:
    return json.loads(fetch(url).decode("utf-8"))


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def dumps_compact(obj) -> bytes:
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def write_json(path: Path, obj, *, pretty: bool = True) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(obj, ensure_ascii=False, indent=2 if pretty else None)
    path.write_text(text + "\n", encoding="utf-8", newline="\n")


def write_gz_json(path: Path, obj) -> bytes:
    """Writes deterministic gzip (mtime 0, no file name) and returns the bytes."""
    raw = dumps_compact(obj)
    buf = io.BytesIO()
    with gzip.GzipFile(filename="", mode="wb", fileobj=buf, compresslevel=9, mtime=0) as gz:
        gz.write(raw)
    data = buf.getvalue()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return data


def read_gz_json(path: Path):
    return json.loads(gzip.decompress(path.read_bytes()).decode("utf-8"))


def load_config() -> dict:
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
