#!/usr/bin/env python3
"""Reports QuranEnc translations whose published version differs from ours.

QuranEnc term 6: keep translations updated to the latest version. Run monthly
(.github/workflows/quranenc-check.yml). Sources:
  - /api/v1/translations/list (version + last_update) for listed keys;
  - old.quranenc.com/en/home ("YYYY-MM-DD - Vx.y.z") for keys missing from the
    list (russian_rwwad, malay_basumayyah, bengali_zakaria). Keys without a
    published version fall back to the date inside downloads/sqlite/<key>.zip
    (none at present; bengali_rwwad was dropped for that reason).

Exit code 0 = up to date, 2 = updates available (the workflow opens an issue),
1 = error. Writes a Markdown report to --report (default: stdout only).

Update procedure: python scripts/quran/fetch_quranenc.py [--only KEY] →
python scripts/quran/verify_quran.py --write → new tag quran-vN (or move the
manifest to a new tag) → copy manifest + bundled files into the app.
"""

from __future__ import annotations

import argparse
import datetime as dt
import io
import json
import re
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from quran_common import TRANSLATIONS_DIR, fetch, fetch_json  # noqa: E402

LIST_URL = "https://quranenc.com/api/v1/translations/list"
OLD_HOME = "https://old.quranenc.com/en/home"
ZIP_URL = "https://quranenc.com/downloads/sqlite/{key}.zip"


def old_site_versions() -> dict[str, tuple[str, str]]:
    html = fetch(OLD_HOME).decode("utf-8", "replace")
    out: dict[str, tuple[str, str]] = {}
    # Each block: "... 2026-03-29 - V1.0.1 ... browse/<key>"
    for match in re.finditer(r"(\d{4}-\d{2}-\d{2}) - V([0-9.]+).{0,600}?/browse/([a-z_]+)", html, re.S):
        out.setdefault(match.group(3), (match.group(2), match.group(1)))
    return out


def zip_date(key: str) -> str:
    info = zipfile.ZipFile(io.BytesIO(fetch(ZIP_URL.format(key=key)))).infolist()[0]
    y, m, d = info.date_time[:3]
    return f"{y:04d}-{m:02d}-{d:02d}"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()

    manifest = json.loads((TRANSLATIONS_DIR / "manifest.json").read_text(encoding="utf-8"))
    listed = {t["key"]: t for t in fetch_json(LIST_URL)["translations"]}
    old = None
    rows, outdated = [], []
    for entry in manifest["translations"]:
        key = entry["key"]
        ours = (entry.get("version"), entry.get("last_update"))
        if key in listed:
            t = listed[key]
            theirs = (t["version"], dt.datetime.fromtimestamp(t["last_update"], tz=dt.timezone.utc).date().isoformat())
            changed = theirs[0] != ours[0]
            source = "list API"
        elif entry.get("version"):
            old = old or old_site_versions()
            theirs = old.get(key, (None, None))
            changed = theirs[0] is not None and theirs[0] != ours[0]
            source = "old.quranenc.com"
        else:
            theirs = (None, zip_date(key))
            changed = theirs[1] != ours[1]
            source = "sqlite zip date"
        rows.append(f"| {key} | {ours[0]} ({ours[1]}) | {theirs[0]} ({theirs[1]}) | {source} | {'UPDATE' if changed else 'ok'} |")
        if changed:
            outdated.append(key)

    report = "\n".join(
        [
            "# QuranEnc version check",
            "",
            "| key | ours | QuranEnc | source | status |",
            "|---|---|---|---|---|",
            *rows,
            "",
            f"Outdated: {', '.join(outdated) if outdated else 'none'}",
        ]
    )
    print(report)
    if args.report:
        args.report.write_text(report + "\n", encoding="utf-8")
    return 2 if outdated else 0


if __name__ == "__main__":
    sys.exit(main())
