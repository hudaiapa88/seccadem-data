#!/usr/bin/env python3
"""Downloads QuranEnc translations and writes quran/v1/translations/*.

QuranEnc terms (https://quranenc.com, "Terms and Policies"): no modification,
addition or deletion; name the publisher and the source (QuranEnc.com); state
the version; keep the version information; send notes to the source; keep up
with new versions; no inappropriate ads next to the translation.

Text and footnotes are stored exactly as returned by
GET /api/v1/translation/sura/{key}/{sura}; nothing is trimmed or rewritten.

Usage: python scripts/quran/fetch_quranenc.py [--offline] [--only KEY ...]
"""

from __future__ import annotations

import argparse
import datetime as dt
import io
import json
import sys
import time
import zipfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from build_tanzil import EXPECTED_AYAHS, UI_LANGS  # noqa: E402
from quran_common import (  # noqa: E402
    CACHE_DIR,
    SURAH_COUNT,
    TRANSLATIONS_DIR,
    fetch,
    fetch_json,
    load_config,
    sha256_bytes,
    write_gz_json,
    write_json,
)

API = "https://quranenc.com/api/v1"
SURA_URL = API + "/translation/sura/{key}/{sura}"
LIST_URL = API + "/translations/list"
SQLITE_ZIP_URL = "https://quranenc.com/downloads/sqlite/{key}.zip"
BROWSE_URL = "https://quranenc.com/en/browse/{key}"
TERMS = (
    "QuranEnc.com Terms and Policies: 1) no modification, addition or deletion of the content; "
    "2) clearly refer to the publisher and the source (QuranEnc.com); 3) mention the version number; "
    "4) keep the version information; 5) notify the source of any note on the translation; "
    "6) update to the latest version issued by the source; 7) no inappropriate advertisements "
    "when displaying the translation."
)


def cache_path(key: str, sura: int) -> Path:
    return CACHE_DIR / "quranenc" / key / f"{sura:03d}.json"


def fetch_sura(key: str, sura: int, offline: bool) -> list[dict]:
    path = cache_path(key, sura)
    if offline and path.exists():
        raw = path.read_bytes()
    else:
        raw = fetch(SURA_URL.format(key=key, sura=sura))
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
        time.sleep(0.15)
    return json.loads(raw.decode("utf-8"))["result"]


def iso_date(ts) -> str | None:
    if ts is None:
        return None
    if isinstance(ts, str):
        return ts
    return dt.datetime.fromtimestamp(int(ts), tz=dt.timezone.utc).date().isoformat()


def zip_date(key: str) -> str:
    data = fetch(SQLITE_ZIP_URL.format(key=key))
    info = zipfile.ZipFile(io.BytesIO(data)).infolist()[0]
    y, m, d = info.date_time[:3]
    return f"{y:04d}-{m:02d}-{d:02d}"


def build_one(entry: dict, listed: dict | None, l10n: dict[str, dict], offline: bool) -> dict:
    key = entry["key"]
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(lambda s: fetch_sura(key, s, offline), range(1, SURAH_COUNT + 1)))

    surahs: list[list[list[str]]] = []
    problems = []
    for number, (rows, expected) in enumerate(zip(results, EXPECTED_AYAHS), start=1):
        rows = sorted(rows, key=lambda r: int(r["aya"]))
        if len(rows) != expected:
            problems.append(f"surah {number}: {len(rows)}/{expected} ayahs")
        if [int(r["aya"]) for r in rows] != list(range(1, len(rows) + 1)):
            problems.append(f"surah {number}: ayah numbers not contiguous")
        empty = [r["aya"] for r in rows if not (r.get("translation") or "").strip()]
        if empty:
            problems.append(f"surah {number}: empty translation at {empty[:5]}")
        surahs.append([[r.get("translation") or "", r.get("footnotes") or ""] for r in rows])
    if problems:
        raise SystemExit(f"{key}: " + "; ".join(problems[:10]))

    fallback = entry.get("fallback") or {}
    if listed:
        title, description = listed["title"], listed["description"]
        version, last_update = listed["version"], iso_date(listed["last_update"])
        direction = listed["direction"]
        version_source = "quranenc.com/api/v1/translations/list"
    else:
        title, description = fallback["title"], fallback["description"]
        version, last_update = fallback.get("version"), fallback.get("last_update")
        direction = "rtl" if entry["lang"] in ("ar", "fa", "ur") else "ltr"
        version_source = fallback.get("versionSource")
        if last_update is None:
            last_update = zip_date(key)

    doc = {
        "format": 1,
        "key": key,
        "lang": entry["lang"],
        "direction": direction,
        "title": title,
        "description": description,
        "translator": entry["translator"],
        "publisher": entry["publisher"],
        "version": version,
        "last_update": last_update,
        "source": "QuranEnc.com",
        "source_url": BROWSE_URL.format(key=key),
        "terms": TERMS,
        "fields": ["translation", "footnotes"],
        "surahs": surahs,
    }
    data = write_gz_json(TRANSLATIONS_DIR / f"{key}.json.gz", doc)

    title_l10n = {}
    for ui, items in l10n.items():
        if key in items and items[key].get("title"):
            title_l10n[ui] = items[key]["title"]
    footnotes = sum(1 for s in surahs for a in s if a[1])
    print(f"{key}: v{version} ({last_update}) {sum(len(s) for s in surahs)} ayahs, {footnotes} with footnotes, {len(data)} bytes")
    return {
        "key": key,
        "lang": entry["lang"],
        "direction": direction,
        "title": title,
        "title_l10n": title_l10n,
        "description": description,
        "translator": entry["translator"],
        "publisher": entry["publisher"],
        "version": version,
        "last_update": last_update,
        "version_source": version_source,
        "sha256": sha256_bytes(data),
        "bytes": len(data),
        "source_url": BROWSE_URL.format(key=key),
        "default": bool(entry.get("default")),
        "bundled": bool(entry.get("bundled")),
        "rights_tier": entry.get("rightsTier"),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--offline", action="store_true")
    parser.add_argument("--only", nargs="*")
    args = parser.parse_args()

    config = [t for t in load_config()["translations"] if t.get("enabled")]
    if args.only:
        config = [t for t in config if t["key"] in args.only]

    listed = {t["key"]: t for t in fetch_json(LIST_URL)["translations"]}
    l10n: dict[str, dict] = {}
    for ui in UI_LANGS:
        items = fetch_json(f"{LIST_URL}?localization={ui}")["translations"]
        l10n[ui] = {t["key"]: t for t in items}

    manifest_path = TRANSLATIONS_DIR / "manifest.json"
    previous = {}
    if manifest_path.exists():
        previous = {t["key"]: t for t in json.loads(manifest_path.read_text(encoding="utf-8"))["translations"]}

    entries = []
    for entry in config:
        entries.append(build_one(entry, listed.get(entry["key"]), l10n, args.offline))
    for key, old in previous.items():
        if key not in {e["key"] for e in entries} and args.only:
            entries.append(old)
    order = {t["key"]: i for i, t in enumerate(load_config()["translations"])}
    entries.sort(key=lambda e: order.get(e["key"], 999))

    write_json(
        manifest_path,
        {
            "format": 1,
            "source": "QuranEnc.com",
            "terms": TERMS,
            "cdn": "https://cdn.jsdelivr.net/gh/hudaiapa88/seccadem-data@quran-v1/quran/v1/translations/",
            "translations": entries,
        },
    )
    print(f"manifest: {len(entries)} translations")


if __name__ == "__main__":
    main()
