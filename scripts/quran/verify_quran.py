#!/usr/bin/env python3
"""Verifies quran/v1 against checksums.json (SHA-256 lock) and content rules.

Checks: 114 surahs / 6236 ayahs / per-surah counts in the Arabic text, the
search text and every translation; Fatiha and Ikhlas verbatim; the Tanzil
copyright block kept; manifest sha256/bytes equal to the files.

Usage:
  python scripts/quran/verify_quran.py           # verify (exit 1 on mismatch)
  python scripts/quran/verify_quran.py --write   # rewrite checksums.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from build_tanzil import EXPECTED_AYAHS, FATIHA_1, IKHLAS  # noqa: E402
from quran_common import (  # noqa: E402
    AYAH_COUNT,
    QURAN_DIR,
    TRANSLATIONS_DIR,
    read_gz_json,
    sha256_file,
    write_json,
)

CHECKSUMS = QURAN_DIR / "checksums.json"


def data_files() -> list[Path]:
    files = [QURAN_DIR / "quran_uthmani.json.gz", QURAN_DIR / "quran_search.json.gz", QURAN_DIR / "quran_meta.json"]
    files += sorted(TRANSLATIONS_DIR.glob("*.json.gz"))
    files.append(TRANSLATIONS_DIR / "manifest.json")
    return files


def check_counts(name: str, surahs: list) -> list[str]:
    errors = []
    if len(surahs) != 114:
        errors.append(f"{name}: {len(surahs)} surahs")
    if sum(len(s) for s in surahs) != AYAH_COUNT:
        errors.append(f"{name}: {sum(len(s) for s in surahs)} ayahs")
    for i, (s, n) in enumerate(zip(surahs, EXPECTED_AYAHS), start=1):
        if len(s) != n:
            errors.append(f"{name}: surah {i} has {len(s)} ayahs, expected {n}")
    return errors


def verify_content() -> list[str]:
    errors = []
    uthmani = read_gz_json(QURAN_DIR / "quran_uthmani.json.gz")
    errors += check_counts("uthmani", uthmani["surahs"])
    if uthmani["surahs"][0][0] != FATIHA_1:
        errors.append("uthmani: Fatiha 1:1 differs")
    if uthmani["surahs"][111] != IKHLAS:
        errors.append("uthmani: Ikhlas differs")
    if "CHANGING IT IS NOT ALLOWED" not in uthmani.get("copyright", ""):
        errors.append("uthmani: Tanzil copyright block missing")
    search = read_gz_json(QURAN_DIR / "quran_search.json.gz")
    errors += check_counts("search", search["surahs"])
    meta = json.loads((QURAN_DIR / "quran_meta.json").read_text(encoding="utf-8"))
    if [s["ayahs"] for s in meta["surahs"]] != EXPECTED_AYAHS:
        errors.append("meta: ayah counts differ")
    for key, size in (("juz", 30), ("pages", 604), ("hizbQuarters", 240), ("sajdas", 15)):
        if len(meta[key]) != size:
            errors.append(f"meta: {key} has {len(meta[key])}")

    manifest = json.loads((TRANSLATIONS_DIR / "manifest.json").read_text(encoding="utf-8"))
    for entry in manifest["translations"]:
        path = TRANSLATIONS_DIR / f"{entry['key']}.json.gz"
        if not path.exists():
            errors.append(f"{entry['key']}: file missing")
            continue
        if sha256_file(path) != entry["sha256"] or path.stat().st_size != entry["bytes"]:
            errors.append(f"{entry['key']}: manifest sha256/bytes mismatch")
        doc = read_gz_json(path)
        errors += check_counts(entry["key"], doc["surahs"])
        empty = sum(1 for s in doc["surahs"] for a in s if not a[0].strip())
        if empty:
            errors.append(f"{entry['key']}: {empty} empty ayahs")
    return errors


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    errors = verify_content()
    if errors:
        raise SystemExit("Content check failed:\n  " + "\n  ".join(errors))

    current = {
        str(p.relative_to(QURAN_DIR)).replace("\\", "/"): {"sha256": sha256_file(p), "bytes": p.stat().st_size}
        for p in data_files()
    }
    if args.write:
        write_json(CHECKSUMS, {"format": 1, "algorithm": "sha256", "files": current})
        print(f"checksums.json written ({len(current)} files)")
        return

    locked = json.loads(CHECKSUMS.read_text(encoding="utf-8"))["files"]
    diff = sorted(set(locked) ^ set(current)) + sorted(k for k in set(locked) & set(current) if locked[k] != current[k])
    if diff:
        raise SystemExit("Checksum lock mismatch: " + ", ".join(diff))
    print(f"OK: {len(current)} files match checksums.json")


if __name__ == "__main__":
    main()
